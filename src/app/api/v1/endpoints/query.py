from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.orm import Session

from app.schemas.query import QueryRequest,QueryResponse,SourceChunk
from app.core.database import get_db
from app.core.logger import get_logger
from app.core.security import get_current_user
from app.models.db import Query,User
from app.services.query_service import answer_question
from app.core.limiter import limiter


logger = get_logger(__name__)

router = APIRouter()


@router.post("", response_model=QueryResponse)
@limiter.limit("30/minute")
def queryLLM(
    request:Request,
    payload: QueryRequest,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    try:
       logger.debug("Reached Query Endpoint")
       answer =  answer_question(repo_id=payload.repo_id, query=payload.query)
       logger.debug(answer)
       new_query =  Query(user_id=current_user.id,repo_id=payload.repo_id,question=payload.query)


       new_query.answer = answer["answer"]
       new_query.source = answer["sources"]

       
       db.add(new_query)
       db.commit()
       db.refresh(new_query)
       sources = [SourceChunk(fileN=i["file"],name=i["name"],start_line=int(i["start_line"]) ,end_line=int(i["end_line"])) for i in answer["sources"]]

       return QueryResponse(answer=new_query.answer, source=sources)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error Occured:{str(e)}" )
        raise HTTPException(status_code=500,detail='Internal Server Error')




