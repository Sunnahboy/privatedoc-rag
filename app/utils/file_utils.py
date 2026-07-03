import re
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from app.config import settings

def sanitize_filename(filename:str)->str:
    """
    Convert an uploaded filename into a safer filename.
    Why:
    - Users can upload files with spaces, symbols, or path tricks.
    - We do not trust user-controlled filenames.
    - We preserve readability but remove dangerous characters.
    Example:
    "../../my report!!.pdf" -> "my_report.pdf"
    """

    name  = Path(filename).name #remove any path parts
    name  = name.replace(" ","_")
    #remove any char that are not letters , numbers , dots etc
    name  = re.sub(r"[^A-Za-z0-9._-]","", name)

    #avoid empty filename after cleaning
    if not name: 
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail="Invalid filename")
    return name

def get_file_extension(filename:str):
    """
    Return the lowercase file extension.
    why:
     -Validation should be case insensitive
     -i.e REPORT.PDF and report.pdf
    """
    return Path(filename).suffix.lower()

def validate_file_extension(filename:str)->None:
    """
    Validate that the uploaded file type is allowed.

    MVP allowed types:
      -PDF
      -TXT
      - Markdown
      - PPT
    """
    extension  = get_file_extension(filename)
    if extension not in settings.allowed_extensions_set:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = f"Unsupported file type '{extension}'. Allowed types: {sorted(settings.allowed_extensions_set)}"
        )

def validate_file_size(file_size:int)->None:
    """
    Validate uploaded file size.
    Why:
    - Large files can consume memory and disk.
    - Upload limits protect the backend from abuse or accidents.
    """
    if  file_size <=0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= f"File too large. Maximum allowed size is {settings.max_upload_bytes} MB.",
        )
    
def ensure_upload_dir()->Path:
    """
    Create upload directory if it does not exit
    why:
     -The app should not crush just because the folder is missing
     -keeps the storage stepup predictable
    """
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True,exist_ok=True)
    return upload_path

