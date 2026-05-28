from openai import OpenAI
import os 
import json
import time
from app.core.logger import get_logger
from app.tools.supabase_tools import (
    get_all_metadata,
    get_file_metadata,
    list_repo_files,
)
from app.tools.qdrant_tools import get_code_chunks, get_file_code_chunks

logger = get_logger(__name__)
api_key = os.getenv("OPENROUTER_API_KEY")

MODEL_ID = "openai/gpt-oss-120b:free"

client  = OpenAI(base_url="https://openrouter.ai/api/v1",
                 api_key=api_key)

# Gemini schema -> OpenAI response_format
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "investigation_report", # OpenAI requires a name for the schema
        "strict": True,                 # Ensures 100% adherence to your keys
        "schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "status": {"type": "string", "enum": ["SOLVED", "INCOMPLETE", "NOT_FOUND"]},
                "files": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "code_chunks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "code": {"type": "string"},
                            "explanation": {"type": "string"}
                        },
                        "required": ["files", "code_chunks", "answer","status"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["answer", "status", "files", "code_chunks"],
            "additionalProperties": False
        }
    }
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "list_repo_files",
            "description": "Fetches the names of all the files of a codebase. Use this to find which files to target.Returns a list of filenames",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "The unique UUID of the repository.",
                    }
                },
                "required": ["repo_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_metadata",
            "description": "Fetches the metadata of a file in a repository. Returns an object containing imports,exports,skeleton structure and summary of the file. Use this to analyse the file structure and data",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "The unique UUID of the repository.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "the path or name of the file in question.",
                    },
                },
                "required": ["repo_id", "file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_metadata",
            "description": "Fetches the metadata of all the files in repository. Returns a list of objects containing filepath, import,export,skeleton and summary of each files. Use it atmost once. Only use when required.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "The unique UUID of the repository.",
                    },
                },
                "required": ["repo_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_code_chunks",
            "description": "Does a vector search on the code chunks based on the query. Returns a list of chunks containing code, start line,end line, filename etc. Use it only in the case of low level search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "The unique UUID of the repository.",
                    },
                    "query": {
                        "type": "string",
                        "description": "the query passed by the user on the codebase",
                    },
                },
                "required": ["repo_id", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_code_chunks",
            "description": "Does a vector search on the code chunks based on the query on a given file. Returns a list of chunks containing code, start line,end line, filename etc. Use it only in the case of low level search within specific a specific.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "The unique UUID of the repository.",
                    },
                    "query": {
                        "type": "string",
                        "description": "the query passed by the user on the codebase",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File path in which the vector search is carried",
                    },
                },
                "required": ["repo_id", "file_path"],
            },
        },
    },
]

available_tools = {  # noqa: F841
        "get_all_metadata": get_all_metadata,
        "get_file_metadata": get_file_metadata,
        "list_repo_files": list_repo_files,
        "get_code_chunks": get_code_chunks,
        "get_file_code_chunks": get_file_code_chunks,
    }


def run_agentic_loop(repo_id: str, query: str):
    # 1. Messages are simple dicts
    messages = [
        {"role": "system", "content": "You are gitlense, a github repository codebase analyst. Your job is to use the tools provided to find answers to the user query using the tools provided to you. With the help of the tools and function calls analyse the query and provide a short summary. CRITICAL:Call the tools using appropriate parameters. Once the evidence is found report immediately"},
        {"role": "user", "content": query}
    ]
    attempt = 1 
    logger.info("Started agentic loop")
    for _ in range(10):
        # 2. Call the model
        logger.info(f"Attempt: {attempt} / 10")
        try:
            
            response = client.chat.completions.create(
                model=MODEL_ID, # Or "google/gemini-2.0-flash-exp:free"
                messages=messages,
                tools=tools,
                response_format=response_format
            )

            response_message = response.choices[0].message
            messages.append(response_message) # Store the model's thought/call

            # 3. Check for tool calls
            if not response_message.tool_calls:
                logger.info("Agent response recieved")
                messages.append(response_message)
                return messages # Return final answer

            # 4. Handle tool calls
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                # Arguments come as a string, must be parsed
                function_args = json.loads(tool_call.function.arguments)
                
                # Inject repo_id
                function_args["repo_id"] = repo_id
                
                # Call your local Python function
                observation = available_tools[function_name](**function_args)

                # 5. Send result back to history
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(observation),
                })
                attempt = attempt + 1 
        except Exception as e:
            if "429" in str(e):
                logger.warning(f"Quota hit! Sleeping for 60 seconds...{str(e).lower()}")
                time.sleep(60)
                attempt = attempt + 1 
                continue
            logger.error(f"CRITICAL ERROR: {str(e).lower()}")
            return {"error": f"{str(e).lower()}"} 

if __name__ == "__main__":
    result = run_agentic_loop(repo_id="9d87b3c0-c72f-4a69-994c-620d0fbdd447", query="Explain the auth system")
    logger.debug(f"result: {result}")