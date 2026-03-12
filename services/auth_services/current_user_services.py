from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime,timezone
from typing import List, Tuple

from db.models.auth_models import User, AuthToken, Role, UserRole  # Update with actual imports
from schemas.auth_schemas import TokenData  # Update with actual schema
from db.session import get_db  # Update with actual DB import
from core.config import settings
from core.logging import TimeZoneLogger

logger = TimeZoneLogger().get_logger()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class CurrentUser:
    def __init__(self, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        self.token = token
        self.db = db
        self.credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.user, self.token_data = self._load_user()

    def _load_user(self) -> Tuple[User, TokenData]:
        try:
            payload = jwt.decode(self.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

            username: str = payload.get("sub")
            token_type: str = payload.get("type")
            if not username or token_type != "ACCESS":
                raise self.credentials_exception
            token_data = TokenData(username=username,jti=self.token)
        except JWTError:
            raise self.credentials_exception

        token_record = (
            self.db.query(AuthToken)
            .filter(AuthToken.token == self.token, AuthToken.revoked == False)
            .first()
        )

        token_record1 = (
            self.db.query(AuthToken)
            .filter( AuthToken.revoked == False,AuthToken.token_type=='REFRESH')
            .first()
        )

        token_data.jti=token_record1.token


        if not token_record or token_record.expires_at < datetime.now(timezone.utc):
            raise self.credentials_exception

        user = self.db.query(User).filter(User.username == token_data.username).first()

        if not user or not user.is_active:
            raise self.credentials_exception

        roles = (
            self.db.query(Role.role_name)
            .join(UserRole)
            .filter(UserRole.user_id == user.user_id)
            .all()
        )
        token_data.roles = [role.role_name for role in roles]

        return user, token_data

    def __call__(self) -> Tuple[User, TokenData]:
        return self.user, self.token_data