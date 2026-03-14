from groq import Groq
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_client = Groq(api_key=settings.GROQ_API_KEY)


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
If the answer is not in the context, say "I couldn't find relevant code for this question. If answer is found give the source as well"

── Code Context ─────────────────────────
{context}

── Question ─────────────────────────────
{question}

── Answer ───────────────────────────────

The required output format is a json :
  answer: text,
  source: json 

source contains: 
found place: Name (from context)
file:  File (from context) 
lines: start_line--end_line (from context) 

Even if multiple lines, and multiple files, list them in the correct order as (found place, file,lines) as a single object for each found places
"""
    return prompt




def ask_llm(question: str, chunks: list[dict]) -> str:
    prompt = build_prompt(question, chunks)

    logger.info(f"Sending query to Groq: {question[:50]}...")

    response = _client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an expert code assistant that answers questions about codebases."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,   # low temperature for factual code answers
        max_tokens=1024,
    )

    answer = response.choices[0].message.content
    logger.info(f"Groq response received")
    return answer