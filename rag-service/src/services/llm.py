from groq import AsyncGroq
from src.core.config import settings
from src.core.logger import get_logger
import json

logger = get_logger(__name__)

_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"""
── Chunk {i+1} ──────────────────────────
File:  {chunk['file']}
Name:  {chunk['name']}
Lines: {chunk['start_line']}-{chunk['end_line']}
Code:
{chunk['code']}
"""
    prompt = f"""You are an expert code assistant. Answer the user's question based ONLY on the code context provided below.
If the answer is not in the context, say "I couldn't find relevant code for this question. If answer is found give the source as well. Always give detailed and brief explanations if answers are found.
Maintain a lightful and friendly tone"

── Code Context ─────────────────────────
{context}

── Question ─────────────────────────────
{question}

Respond in this EXACT JSON format, nothing else:
{{
    "answer": "your detailed answer here",
    "sources":[{{
        "file": "exact file path from context","
        name": "function or class name",
        "type": "node type","
        start_line": line number,
        "end_line": line number
        }}]
}}

source contains: 
found place: Name (from context)
file:  File (from context) 
start_line: start_line (from context)
end_line: end_line (from context) 

Even if multiple lines, and multiple files, list them in the correct order as (found place, file,lines) as a single object for each found places
"""
    return prompt




async def ask_llm(question: str, chunks: list[dict]) -> str:
    prompt = build_prompt(question, chunks)

    logger.info(f"Sending query to Groq: {question[:50]}...")

    response = await _client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are GitLense, an expert code assistant that answers questions about codebases."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1,   # low temperature for factual code answers
        max_tokens=2048,
    )

    raw = response.choices[0].message.content
    logger.info("Groq response received")
    try:
        # strip markdown code blocks if LLM adds them
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean)
        return result

    except json.JSONDecodeError:
        logger.error(f"LLM returned invalid JSON: {raw}")
        # ── fallback: return raw text if JSON parsing fails
        return {
            "answer":  raw,
            "sources": []
        }

