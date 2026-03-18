from app.services.embedder import embed_query
from app.services.vector import search_embeddings
from app.services.llm import ask_llm
from app.core.logger import get_logger

import uuid

logger = get_logger(__name__)


def answer_question(repo_id:str, query:str):
    try:

        query_embed = embed_query(query)
        logger.debug(f"query embedded : length: {len(query_embed)}")

        chunks = search_embeddings(repo_id=repo_id, query_vector=query_embed)
        logger.debug(f"Obtained {len(chunks) } chunks")
        for chunk in chunks :
            logger.debug(chunk["code"])
        result = ask_llm(question=query, chunks=chunks)

        logger.info(f"\nanswer:{result['answer']}")
        for source in result['sources']:
            logger.debug(source)

        return result
    except Exception as e:
        print("Exception")

if __name__ == "__main__":
    answer_question(uuid.UUID("e448a4f1-4960-457c-ad70-1482b5ae59f6"),"how does the auth work")