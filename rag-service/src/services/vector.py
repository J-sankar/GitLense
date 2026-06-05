
from src.core.qdrant import qdrant_client as client
from qdrant_client import models
from src.core.logger import get_logger
from src.utils.compression import decompress_code
logger = get_logger(__name__)






    
async def search_embeddings(repo_id:str, query_vector:str, top_k : int = 5) ->list[dict] :
    collection  = f"repo_{repo_id}"

    try:
        results = await client.query_points(
            collection_name = collection,
            query = query_vector,
            limit = top_k
        )
        results = results.points
        logger.debug(type(results))
    except Exception as e :
        logger.debug(str(e))
    




    chunks = []

    for r in results:
        chunks.append({
            "code":       decompress_code(r.payload["code"]),
            "file":       r.payload["file"],
            "language":   r.payload["language"],
            "type":       r.payload["type"],
            "name":       r.payload["name"],
            "start_line": r.payload["start_line"],
            "end_line":   r.payload["end_line"],
            "score":      r.score  
        })

    return chunks 


async def search_file_chunks(repo_id: str, file_path: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
    """
    Searches for semantic matches strictly within a single file using metadata filters.
    """
    logger.info(f"Scoped search in: {file_path}")
    collection = f"repo_{repo_id}"
    
    try:
        results = await client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=top_k,
            # Filter matches the file_path stored in your metadata (payload)
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="file", # This must match your key in Qdrant payload
                        match=models.MatchValue(value=file_path)
                    )
                ]
            ),
            with_payload=True
        )

        chunks = []
        for r in results.points:
            chunks.append({
                "code": decompress_code(r.payload.get("code", "")),
                "start_line": r.payload.get("start_line"),
                "end_line": r.payload.get("end_line"),
                "score": round(r.score, 4)
            })
        
        return chunks

    except Exception as e:
        logger.error(f"Scoped search failed: {str(e)}")
        return [{"error": str(e)}]




