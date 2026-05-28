import json

from google import genai
from app.core.config import settings
from app.tools import qdrant_tools as vector_tools , supabase_tools as db_tools
from pydantic import BaseModel,Field
from typing import List,Literal, Optional
from app.core.logger import get_logger
import asyncio
logger = get_logger(__name__)
import time
MODEL_ID = "gemini-2.5-flash"
client = genai.Client(api_key=settings.GEMINI_API_KEY)

SYSTEM_PROMPT = """ROLE: Senior Codebase Architect & Planner
GOAL: Analyze a user's query and generate a precise navigation plan for a codebase RAG pipeline.

### CONTEXT
You have access to a repository's metadata. Your task is NOT to answer the user's question directly with code, but to identify WHERE the answer lies and WHAT strategy should be used to retrieve it.

### YOUR TOOLS
1. search_summaries(repo_id,query): Use this to find files by technical keywords or intent. The 'query' should be technical (e.g., 'jwt verification' instead of 'how do I login').
2. list_repo_files(repo_id): Returns a list of all file paths in the repository.
3. global_semantic_search(repo_id, query): Use this for conceptual queries where file names are ambiguous (e.g., 'error handling strategy').

### STRATEGY GUIDELINES
- PHASE 1 (Discovery): Use tools to narrow down the codebase. If the entry point is obvious from the tree, skip to Phase 2.
- PHASE 2 (Planning): Identify the "Primary Entry Point" (usually a Controller or API Route) and "Secondary Logic" (Services, Utils, or Models).
- PHASE 3 (Handover): Output the final plan in the required JSON format.

### CONSTRAINTS
- Limit 'starting_files' to a maximum of 3 files.
- Ensure the 'strategy' explains HOW the next agent should trace the logic (e.g., "Follow imports from the Controller to the Service layer").
- If the query is irrelevant to the codebase, inform the user.

### OUTPUT SCHEMA (JSON)
You must output ONLY a valid JSON object following this structure:
{
  "thought_process": "Brief explanation of why these files were chosen.",
  "primary_intent": "The categorized intent of the user (e.g., Debugging, Feature Discovery, Architecture Overview).",
  "starting_files": ["path/to/file1", "path/to/file2"],
  "search_strategy": "metadata_tracing | semantic_broadening | dependency_mapping",
  "next_steps_instructions": "Specific guidance for the Navigator agent."
}"""

AVAILABLE_TOOLS = {
    "list_repo_files": db_tools.list_repo_files,
    "get_file_metadata": db_tools.get_file_metadata,
    "search_summaries": db_tools.get_summaries,
    "global_semantic_search": vector_tools.get_code_chunks
}

ARCHITECT_TOOLS_CONFIG = [
    {
        "name": "list_repo_files",
        "description": "Returns a list of all file paths in the repository.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_file_metadata",
        "description": "Returns imports, exports, and skeleton of a specific file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file."}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "search_summaries",
        "description": "Search for specific keywords in file summaries.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Technical search query."}
            },
            "required": ["query"]
        }
    }
]


class Step(BaseModel):
    step_number: int = Field(description="The sequential order of the step")
    tool: Literal["search_summaries", "list_repo_files", "global_semantic_search", "get_file_metadata"] = Field(
        description="The specific tool to be used in this step"
    )
    path: Optional[str] = Field(
        None, description="The file path or directory path, if applicable to the tool"
    )
    reason: str = Field(description="Why this step is necessary for the overall plan")


class  ArchitectResponse(BaseModel):
    thought_process: str = Field(
        description="Brief internal reasoning on how the project structure relates to the user query"
    )
    primary_intent: Literal["feature_exploration", "debugging", "dependency_tracing", "refactoring"] = Field(
        description="The classified intent of the user's request"
    )
    steps: List[Step] = Field(min_items=1, max_items=5)


async def run_architect_agent(repo_id: str, query: str):
    # 1. Initialize the conversation
    messages = [
        {"role": "user", "parts": [{"text": f"User Query: {query}\nRepo ID: {repo_id}"}]}
    ]

    # 2. Iterative loop (limit turns to prevent infinite loops)
    response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config={
                "tools": [{"function_declarations": ARCHITECT_TOOLS_CONFIG}],
                "system_instruction": SYSTEM_PROMPT
            })

        
        # Check if Gemini wants to call a tool
    


            
            # Execute the local tool (Injecting repo_id automatically)
          
            # Add the tool request and the response to message history
             # Go back to the model with new data
            
        # If no tool call, Gemini has reached its conclusion

    
    return ArchitectResponse(**json.loads(response.text))

    return {"error": "Max iterations reached without a plan."}


if __name__ == "__main__":
    asyncio.run(run_architect_agent(repo_id="9d87b3c0-c72f-4a69-994c-620d0fbdd447", query= "how does the authentication work"))
