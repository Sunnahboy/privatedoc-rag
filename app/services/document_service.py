import shutil
from pathlib import Path
from fastapi import UploadFile

from app.schemas.document_schema import DocumentUploadResponse
from app.utils.file_utils import(
    ensure_upload_dir,
    get_file_extension,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
)
from app.utils.id_id_utils import generate_document_id

def save_uploaded_document(file:UploadFile)-> DocumentUploadResponse:
    """
    Validate and save an uploaded document
    why this logic is in service:
     -API route should stay thin.
     -File validation and saving are business logic
     -Later, this service will call the PDF extraction, chucking,embeddings, and metadata store
    
    """

    if file.filename is None:
        raise ValueError("Uploaded file must have a filename.")
    
    original_filename  = file.filename
    safe_filename  = sanitize_filename(original_filename)
    
    validate_file_size(safe_filename)

    validate_file_extension(file.size)#uses native file.size attribute safely

    document_id  = generate_document_id()
    extension  = get_file_extension(sanitize_filename)
    Upload_dir  = ensure_upload_dir()

    #store as doc_id + original safe extension
    stored_filename  = f"{document_id}{extension}"
    saved_path: Path  = Upload_dir / stored_filename

    
    #Copy uploaded file stream to disk.
    #Why not file.file.read() into memory?
    #Because large files should be streamed instead of loaded fully into RAM.
     
    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return DocumentUploadResponse(
        document_id=document_id,
        filename=stored_filename,
        original_filename= original_filename,
        file_extension=extension,
        file_size_bytes=file.size,
        status="uploaded",
        saved_path=str(saved_path)
    )
        
