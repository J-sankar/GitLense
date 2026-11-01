
import math
from src.core.qdrant import qdrant_client as client
from src.core.redis import redis_manager
from qdrant_client.models import Distance, PointStruct, VectorParams
from qdrant_client import models
from src.core.logger import get_logger
from src.utils.compression import compress_code 
from src.utils.crypto import get_deterministic_id
logger = get_logger(__name__)



async def get_or_create_collection(repo_id:str,vector_size: int):
    collection_name = f"repo_{repo_id}"
    exists = await client.collection_exists(collection_name)
    if not exists:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size, 
                distance=Distance.COSINE
            )
        )
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="file",
            field_schema=models.KeywordIndexParams(
                type="keyword"
            )
        )
        logger.info(f"Created collection and payload index for {collection_name}")
    
    return collection_name


async def store_embeddings_batch(repo_id: str, chunks: list[dict]) -> int:
    if not chunks:
        return 0
    try:
        lock_name = f"lock:repo:{repo_id}"

    # Lock it at the Redis level!
        async with redis_manager.lock(lock_name):
            collection = await get_or_create_collection(repo_id, len(chunks[0]["vector"]))

        batch_size = 10
        batch_length = math.ceil(len(chunks)/batch_size)
        batch_count = 1 

        for i in range(0, len(chunks), batch_size) :
            batch = chunks[i:i+batch_size]
            logger.info(f"Storing batch {batch_count}/{batch_length} ")
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
            await client.upsert(
                collection_name=collection,
                points= points
            )
            batch_count += 1 
        return len(chunks)
    except Exception as e:
        logger.error(f"Error storing embeddings: {str(e).lower()}")
        raise 


async def get_chunks_count(repo_id:str) ->int:
    collection = f"repo_{repo_id}"
    try:
        info = await client.get_collection(collection_name=collection)
        return info.points_count
    except Exception:
        return 0 
        

    





async def delete_embeddings(repo_id: str):
    try:
        await client.delete_collection(f"repo_{repo_id}")
    except Exception:
        pass


