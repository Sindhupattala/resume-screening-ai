from pydantic import BaseModel
from typing import Optional, List


# Pydantic Models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    jti:str=None
    username: Optional[str] = None
    roles: Optional[List[str]] = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    roles: List[str]

class RoleCreate(BaseModel):
    role_name: str
    description: Optional[str] = None

class PermissionCreate(BaseModel):
    permission_name: str
    description: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: str

class PasswordReset(BaseModel):
    token: str
    new_password: str