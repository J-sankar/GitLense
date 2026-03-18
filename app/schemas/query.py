from pydantic import BaseModel, HttpUrl
from uuid import UUID


class QueryRequest(BaseModel):
    repo_id: str
    query: str



class SourceChunk (BaseModel):
    fileN: str
    name : str
    start_line: int
    end_line: int 


class QueryResponse (BaseModel):
    answer: str
    source : list[SourceChunk]


