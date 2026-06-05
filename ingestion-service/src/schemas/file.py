from pydantic import BaseModel, Json
from typing import Any,List


class FileUpload(BaseModel):
    repo_id : str
    job_id : str 
    repo_url : str
    file_path: str
    language: str
    content: str
    retries: str 


# 1. The fully flattened FileMetadata model
class FileMetadata(BaseModel):
    # The 'disintegrated' inner metadata fields
    path: str
    imports: List[str]      # Use list[str] if it's a list!
    exports: List[str]
    language: str
    skeleton: Any
    
    # The standard file metadata fields
    file_path: str
    file_hash: str
    summary: str

# 2. The main Payload coming from Redis
class Payload(BaseModel):
    repo_id: str          
    job_id: str
    file_path: str
    chunks_indexed: int    
    
    # Pydantic will still auto-parse these JSON strings
    embedded_chunks: Json[List[dict]]         
    file_metadata: Json[FileMetadata]  
    
    retries: int


