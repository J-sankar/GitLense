from fastapi import APIRouter, Depends, HTTPException, Request
from src.schemas.query import QueryRequest, QueryResponse, SourceChunk
from src.core.database import get_db, AsyncSession
from src.core.logger import get_logger
from src.models.db import Query
from src.core.security import get_gateway_user
from src.services.query_service import answer_question
import uuid

logger = get_logger(__name__)

router = APIRouter()


async def get_user_id(x_user_id ):
    if not x_user_id:
        # Fallback for local testing when the header is missing
        raise HTTPException(status_code=401, detail="User id is required")

    return str(x_user_id)


@router.post("", response_model=QueryResponse)
async def queryLLM(
    request: Request,
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user:uuid.UUID = Depends(get_gateway_user),
):
    try:
        
        logger.debug("Reached Query Endpoint")
        answer = await answer_question(repo_id=payload.repo_id, query=payload.query)
        logger.debug(answer)
        new_query = Query(
            user_id=current_user, repo_id=payload.repo_id, question=payload.query
        )

        new_query.answer = answer["answer"]
        new_query.source = answer["sources"]

        db.add(new_query)
        await db.commit()
        await db.refresh(new_query)
        sources = [
            SourceChunk(
                fileN=i["file"],
                name=i["name"],
                start_line=int(i["start_line"]),
                end_line=int(i["end_line"]),
            )
            for i in answer["sources"]
        ]

        return QueryResponse(answer=new_query.answer, source=sources)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error Occured:{str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
