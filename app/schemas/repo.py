from pydantic import BaseModel,HttpUrl
from typing import Literal
from datetime import datetime

class RepoResponse(BaseModel):
    id: str
    name: str
    url: str
    status:  Literal["queued", "processing", "completed", "failed"]
    chunks_indexed: int
    created_at: datetime
    error: str | None=None
