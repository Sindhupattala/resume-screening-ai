from sqlalchemy import  Column, BigInteger, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from db.session import Base


# Enums
class TokenType(str, enum.Enum):
    ACCESS = "ACCESS"
    REFRESH = "REFRESH"
# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    auth_tokens = relationship("AuthToken", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    roles = relationship("Role", secondary="user_roles", back_populates="users")

class Role(Base):
    __tablename__ = "roles"
    role_id = Column(BigInteger, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")

class Permission(Base):
    __tablename__ = "permissions"
    permission_id = Column(BigInteger, primary_key=True)
    permission_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(BigInteger, ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime, server_default=func.current_timestamp())

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(BigInteger, ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(BigInteger, ForeignKey("permissions.permission_id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime, server_default=func.current_timestamp())

class AuthToken(Base):
    __tablename__ = "auth_tokens"
    token_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    token_type = Column(Enum(TokenType), nullable=False)
    issued_at = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    user = relationship("User", back_populates="auth_tokens")
    sessions = relationship("Session", back_populates="auth_token")

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    reset_token_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token_id = Column(BigInteger, ForeignKey("auth_tokens.token_id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    is_active = Column(Boolean, default=True)
    last_accessed = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    user = relationship("User", back_populates="sessions")
    auth_token = relationship("AuthToken", back_populates="sessions")
