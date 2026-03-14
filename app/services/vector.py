import chromadb

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH)


def get_collection(repo_id: str):
    return chroma_client.get_or_create_collection(
        name = f"repo_{repo_id}",
        metadata={"hnsw:space": "cosine"}
    )

def store_embeddings(repo_id: str, chunks: list[dict])->int:
    collection = get_collection(repo_id)

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
    collection  = get_collection(repo_id=repo_id)

    if collection.count() == 0:
        raise Exception(f"No embeddings found for repo {repo_id}")


    results = collection.query(query_embeddings=query_vector,
                               n_results=top_k, 
                               include=["documents","metadatas","distances"])

    chunks = []

    for i in range(len(results["ids"][0])):
        chunks.append({
            "code":       results["documents"][0][i],
            "file":       results["metadatas"][0][i]["file"],
            "language":   results["metadatas"][0][i]["language"],
            "type":       results["metadatas"][0][i]["type"],
            "name":       results["metadatas"][0][i]["name"],
            "start_line": results["metadatas"][0][i]["start_line"],
            "end_line":   results["metadatas"][0][i]["end_line"],
            "score":      1 - results["distances"][0][i]  # cosine similarity
        })

    return chunks 



