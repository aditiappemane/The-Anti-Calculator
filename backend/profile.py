from typing import List, Optional
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from backend import crud, schemas, models
from backend.database import get_db
from backend.auth import get_current_user

router = APIRouter()

# Directory to store uploaded documents (create if it doesn't exist)
UPLOAD_DIRECTORY = "./uploads"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

@router.get("/profile", response_model=schemas.User)
async def read_user_profile(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=schemas.User)
async def update_user_profile(user_update: schemas.UserUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = crud.update_user(db, user_id=current_user.id, user_update=user_update)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.post("/profile/documents", response_model=schemas.Document)
async def upload_document(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Save the file locally
    file_location = os.path.join(UPLOAD_DIRECTORY, f"{current_user.id}_{file.filename}")
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create a new document entry in the database
    document_create = schemas.DocumentCreate(
        file_name=file.filename,
        file_type=file.content_type
    )
    db_document = crud.create_user_document(db, document=document_create, owner_id=current_user.id, file_path=file_location)
    return db_document

@router.get("/profile/documents", response_model=List[schemas.Document])
async def get_user_documents(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    documents = crud.get_user_documents(db, owner_id=current_user.id)
    return documents

@router.delete("/profile/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_document = crud.get_document(db, document_id=document_id)
    if not db_document or db_document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found or not authorized")

    # Delete the file from local storage
    if os.path.exists(db_document.file_path):
        os.remove(db_document.file_path)

    crud.delete_user_document(db, document_id=document_id)
    return
