from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext
from typing import List, Optional
from . import models

from backend import models, schemas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    # bcrypt has a password length limit of 72 bytes (when utf-8 encoded).
    # We'll truncate the password to safely fit this limit if it exceeds it.
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return pwd_context.hash(password_bytes.decode('utf-8', 'ignore'))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ---------------------------------------------------------------------------
# User CRUD Operations
# ---------------------------------------------------------------------------

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    db.delete(db_user)
    db.commit()
    return db_user

# ---------------------------------------------------------------------------
# UserDocument CRUD Operations
# ---------------------------------------------------------------------------

def get_document(db: Session, document_id: int) -> Optional[models.UserDocument]:
    return db.query(models.UserDocument).filter(models.UserDocument.id == document_id).first()

def get_user_documents(db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[models.UserDocument]:
    return db.query(models.UserDocument).filter(models.UserDocument.owner_id == owner_id).offset(skip).limit(limit).all()

def create_user_document(db: Session, document: schemas.DocumentCreate, owner_id: int, file_path: str) -> models.UserDocument:
    db_document = models.UserDocument(
        file_name=document.file_name,
        file_path=file_path,
        file_type=document.file_type,
        extracted_salary_data=document.extracted_salary_data, # Added this line
        owner_id=owner_id,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def delete_user_document(db: Session, document_id: int) -> Optional[models.UserDocument]:
    db_document = get_document(db, document_id)
    if not db_document:
        return None
    db.delete(db_document)
    db.commit()
    return db_document

def get_user_documents_by_owner_id(db: Session, owner_id: int, limit: int = 1):
    return (
        db.query(models.UserDocument)
        .filter(models.UserDocument.owner_id == owner_id)
        .order_by(models.UserDocument.uploaded_at.desc())
        .limit(limit)
        .all()
    )

