from pydantic import BaseModel

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
    status:str
    saved_path:str # Later will change this to avoid exposing raw in internal path
