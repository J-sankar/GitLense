from src.services.embedder import embed_query
from src.services.vector import search_embeddings
from src.services.llm import ask_llm
from src.core.logger import get_logger

from fastapi import HTTPException,status

import uuid

logger = get_logger(__name__)


async def answer_question(repo_id:str, query:str):
    try:
        logger.debug("Embedding question")
        query_embed = await embed_query(query)
        logger.debug(f"query embedded : length: {len(query_embed)}")

        chunks = await search_embeddings(repo_id=repo_id, query_vector=query_embed)
        logger.debug(f"Obtained {len(chunks) } chunks")
        for chunk in chunks :
            logger.debug(chunk["code"])
        result = await ask_llm(question=query, chunks=chunks)

        logger.info(f"\nanswer:{result['answer']}")
        # for source in result['sources']:
        #     logger.debug(source)

        return result
    except Exception as e:
        err = str(e).lower()
        if "rate limit" in err or "quota" in err:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="Your have reached your current quota, please try again later or upgrade for better limits")
        else:
            logger.error(f"Exception, {str(e)}")
            raise


if __name__ == "__main__":
    answer_question(uuid.UUID("e448a4f1-4960-457c-ad70-1482b5ae59f6"),"how does the auth work")