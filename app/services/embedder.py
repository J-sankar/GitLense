from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)



if settings.EMBEDDING_PROVIDER == "voyage":
    import voyageai
    _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)

    def _embed_documents(texts: list[str]) -> list[list[float]]:
        result = _client.embed(texts, model="voyage-code-2", input_type="document")
        return result.embeddings

    def _embed_query(text: str) -> list[float]:
        result = _client.embed([text], model="voyage-code-2", input_type="query")
        return result.embeddings[0]

elif settings.EMBEDDING_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    def _embed_documents(texts: list[str]) -> list[list[float]]:
        return [
        genai.embed_content(
            model="models/gemini-embedding-001",
            content=t,
            task_type="retrieval_document"
        )["embedding"]
        for t in texts
    ]
    def _embed_query(text: str) -> list[float]:
        return genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_query"
    )["embedding"]

else:
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")


def build_embed_text(chunk: dict) -> str:
    return f"""File: {chunk['file']}
    Name: {chunk['name']}
    Type: {chunk['type']}
    Lines: {chunk['start_line']}-{chunk['end_line']}
    {chunk['code']}""".strip()

def embed_chunks(chunks: list[dict]) -> list[dict]:
    embedded_chunks = []
    batch_size = 128
    batch_count = 1
    batch_length = batch_size // len(chunks) + 1 

    for i in range(0, len(chunks), batch_size):
        logger.info(f"Embedding started for batch: {batch_count} / {batch_length} ")
        batch  = chunks[i:i + batch_size]
        texts  = [build_embed_text(chunk) for chunk in batch]
        vectors = _embed_documents(texts)

        for j, chunk in enumerate(batch):
            embedded_chunks.append({
                **chunk,
                "vector": vectors[j]
            })

        logger.info(f"Embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")
        batch_count = batch_count + 1 


    logger.info(f"Embedding complete: {len(embedded_chunks)} chunks")     
    return embedded_chunks


def embed_query(text: str) -> list[float]:
    result = _embed_query(text)
    logger.debug(f"Embedded query: {text[:50]}...")
    return result