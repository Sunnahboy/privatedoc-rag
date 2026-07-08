from pydantic import BaseModel
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    """
    Response  returned after a document is uploaded

    why use a schema
      -It gives the API a clear contract
      -FastAPI can document it automatically in /docs
      -The frontend knows exactly what fields to expect
    """
    document_id:str
    filename:str
    original_filename:str
    file_extension:str
    file_size_bytes:int
    storage_provider:int
    storage_key:str#expose for now ,for debug , will hide later for normal users
    status:str
    total_pages:int
    total_chunks:int
    created_at:datetime
    #saved_path:str # Later will change this to avoid exposing raw in internal path


class DocumentListItem(BaseModel):
  """
  One document item returned by GET /documents.
  """

  document_id: str
  filename: str
  original_filename: str
  file_extension: str
  file_size_bytes: int
  storage_provider: str
  storage_key: str #expose for now ,for debug , will hide later for normal users
  status: str
  total_pages: int
  total_chunks: int
  created_at: datetime
  updated_at: datetime

class DocumentDeleteResponse(BaseModel):
  """
  Response returned after deleting a document.
  """
  document_id: str
  deleted: bool
    
        
