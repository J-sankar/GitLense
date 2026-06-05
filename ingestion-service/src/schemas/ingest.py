from pydantic import BaseModel
from uuid import UUID

class IngestRequest(BaseModel):
    repo_url: str


class IngestResponse(BaseModel):
    job_id:  UUID
    repo_id: UUID
    status:  str
    message: str | None = None

class JobStatusResponse(BaseModel):
    job_id:       UUID
    repo_id:      UUID
    status:       str
    progress:     int
    error:        str | None = None
    started_at:   str | None = None
    completed_at: str | None = None
