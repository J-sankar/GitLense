from typing import List
from app.services.embedder import embed_query 
from app.services.vector import search_embeddings,search_file_chunks
from app.core.logger import get_logger
logger = get_logger(__name__)



def get_code_chunks(repo_id:str, query:str) ->List[dict] :
    logger.info(f"Tool call: get code chunks (repo_id : {repo_id[:8]}, query: ${query[:8]}...)")
    try:
        
        query_vector = embed_query(text=query)
        logger.info("Obtained query vector")
        code_chunks = search_embeddings(repo_id=repo_id,query_vector=query_vector)
        if not code_chunks:
            logger.info("No match found")
            return []
        logger.info(f"Obtained code chunks: {len(code_chunks)}")
        return code_chunks
    except Exception as e:
        raise Exception(f"ERROR in tool call (get code chunks) : {str(e).lower()}")

def get_file_code_chunks(repo_id:str, query:str, file_path:str) ->List[dict]:
    logger.info(f"Tool call: get file code chunks (repo_id : {repo_id[:8]}, query: ${query[:8]}...)")
    try:

        query_vector = embed_query(text=query)
        logger.info("Obtained query vector")
        code_chunks = search_file_chunks(repo_id=repo_id,query_vector=query_vector,file_path=file_path)
        if not code_chunks:
            logger.info("No match found")
            return []
        logger.info(f"Obtained code chunks: {len(code_chunks)}")
        return code_chunks
    except Exception as e:
        raise Exception(f"ERROR in tool call (get file code chunks) : {str(e).lower()}")

