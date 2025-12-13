from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    first_name: str
    last_name: str
    phone_number: str


class UserUpdate(UserBase):
    pass

class UserInDBBase(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    file_name: str
    file_type: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentInDBBase(DocumentBase):
    id: int
    file_path: str
    owner_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

class Document(DocumentInDBBase):
    pass

class User(UserInDBBase):
    documents: List[Document] = []

# JWT Token related schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
