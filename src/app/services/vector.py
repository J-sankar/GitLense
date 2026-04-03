
import math
from app.core.qdrant import qdrant_client as client
from qdrant_client.models import Distance, PointStruct, VectorParams
 
from app.core.logger import get_logger
from app.utils.compression import compress_code ,decompress_code
from app.utils.crypto import get_deterministic_id
logger = get_logger(__name__)



def get_or_create_collection(repo_id:str,vector_size: int):
    collection_name = f"repo_{repo_id}"
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size, 
                distance=Distance.COSINE
            )
        )
    
    return collection_name


def store_embeddings_batch(repo_id: str, chunks: list[dict]) -> int:
    collection = get_or_create_collection(repo_id, len(chunks[0]["vector"]))

    batch_size = 10
    batch_length = math.ceil(len(chunks)/batch_size)
    batch_count = 1 

    for i in range(0, len(chunks), batch_size) :
        batch = chunks[i:i+batch_size]
        logger.info(f"-----Storing batch {batch_count}/{batch_length} ")
        points = [
            PointStruct(
                id      = get_deterministic_id(filename=chunk["file"], code=chunk["code"]),
                vector  = chunk["vector"],
                payload = {
                    "point_id": chunk["point_id"],
                    "name":       chunk["name"],
                    "file":       chunk["file"],
                    "language":   chunk["language"],
                    "parent_scope": chunk["parent_scope"],
                    "type":       chunk["type"],
                    "start_line": chunk["start_line"],
                    "end_line":   chunk["end_line"],
                    "code":       compress_code(chunk["code"])
                }
            )
            for chunk in batch
        ]
        client.upsert(
            collection_name=collection,
            points= points
        )
        batch_count += 1 
    return len(chunks)


def get_chunks_count(repo_id:str) ->int:
    collection = f"repo_{repo_id}"
    try:
        info = client.get_collection(collection_name=collection)
        return info.points_count
    except Exception:
        return 0 
        

    
def search_embeddings(repo_id:str, query_vector:str, top_k : int = 5) ->list[dict] :
    logger.debug("QUery Reached here")
    collection  = f"repo_{repo_id}"

    try:
        results = client.query_points(
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


def delete_embeddings(repo_id: str):
    try:
        client.delete_collection(f"repo_{repo_id}")
    except Exception:
        pass


