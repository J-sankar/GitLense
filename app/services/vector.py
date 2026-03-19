import chromadb
import math

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
import uuid 
from app.core.config import settings
from app.core.logger import get_logger
from app.utils.compression import compress_code ,decompress_code

logger = get_logger(__name__)

chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH)


client = QdrantClient(
    url=settings.QDRANT_URL, 
    api_key=settings.QDRANT_API_KEY,
)

print(client.get_collections())

def get_collection(repo_id: str):
    return chroma_client.get_or_create_collection(
        name = f"repo_{repo_id}",
        metadata={"hnsw:space": "cosine"}
    )
def get_or_create_collection(repo_id:str,vector_size: int):
    collection_name = f"repo_{repo_id}"
    try:
        client.get_collection(collection_name=collection_name)
    except:
        client.create_collection(
            collection_name=collection_name,
            vectors_config= VectorParams(
                size=vector_size,
                distance = Distance.COSINE
                )
            )
    return collection_name


def store_embeddings_batch(repo_id: str, chunks: list[dict]) -> int:
    collection = get_or_create_collection(repo_id, len(chunks[0]["vector"]))

    batch_size = 10
    batch_length = math.ceil(len(chunks)/batch_size)
    batch_count = 1 

    for i in range(0, len(chunks), batch_size) :
        batch = chunks[i:i+batch_size+1]
        logger.info(f"Storing batch {batch_count}/{batch_length} ")
        points = [
            PointStruct(
                id      = str(uuid.uuid4()),
                vector  = chunk["vector"],
                payload = {
                    "name":       chunk["name"],
                    "file":       chunk["file"],
                    "language":   chunk["language"],
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
    except:
        return 0 
        

    collection = get_collection

    existing_count = collection.count()
    if existing_count > 0:
        logger.info(f"Repo {repo_id} already has {existing_count} chunks in ChromaDB, skipping store")
        return existing_count
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        ids.append(f"{repo_id}_chunk_{i}")
        embeddings.append(chunk["vector"])
        documents.append(chunk["code"])

        metadatas.append({
            "file": chunk["file"],
            "language": chunk["language"],
            "type" : chunk["type"],
            "name" : chunk["name"],
            "start_line": int(chunk["start_line"]),
            "end_line": int(chunk["end_line"])
        })

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    return len(chunks)

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
            "score":      r.score  # cosine similarity
        })

    return chunks 


def delete_embeddings(repo_id: str):
    try:
        client.delete_collection(f"repo_{repo_id}")
    except:
        pass


