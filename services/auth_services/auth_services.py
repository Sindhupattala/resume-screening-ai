from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from db.models.auth_models import User, AuthToken, Session as DBSession, PasswordResetToken, UserRole, Role
from schemas.auth_schemas import UserCreate, Token
from services.auth_services.utils import UtilityFunctions
from db.models.auth_models import TokenType
from core.config import settings
from core.logging import TimeZoneLogger

logger = TimeZoneLogger().get_logger()

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.utility = UtilityFunctions()

    def create_user(self, user: UserCreate) -> User:
        try:
            logger.info("Creating a new user", extra={"username": user.username})

            db_user = self.db.query(User).filter(User.username == user.username).first()
            if db_user:
                logger.warning("Username already exists", extra={"username": user.username})
                raise HTTPException(status_code=400, detail="Username already registered")

            db_user = self.db.query(User).filter(User.email == user.email).first()
            if db_user:
                logger.warning("Email already exists", extra={"email": user.email})
                raise HTTPException(status_code=400, detail="Email already registered")

            hashed_password = self.utility.get_password_hash(user.password)
            db_user = User(
                username=user.username,
                email=user.email,
                password_hash=hashed_password,
                first_name=user.first_name,
                last_name=user.last_name
            )
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            logger.info("User created successfully", extra={"user_id": db_user.user_id})
            return db_user

        except HTTPException as he:
            logger.error(f"HTTP error during user creation: {he.detail}", exc_info=True)
            raise
        except Exception as e:
            logger.exception("Unexpected error occurred while creating user")
            raise HTTPException(status_code=500, detail="Internal server error")

    def create_token_pair(self, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Token:
        try:
            logger.info("Generating token pair for user", extra={"user_id": user.user_id})

            access_token, access_expire = self.utility.create_token(
                username=user.username,
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                token_type="ACCESS"
            )
            refresh_token, refresh_expire = self.utility.create_token(
                username=user.username,
                expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                token_type="REFRESH"
            )

            access_token_id, refresh_token_id = self.utility.store_tokens(
                db=self.db,
                user_id=user.user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                access_expire=access_expire,
                refresh_expire=refresh_expire
            )
            self.utility.create_session(
                db=self.db,
                user_id=user.user_id,
                token_id=access_token_id,
                expires_at=access_expire,
                ip_address=ip_address,
                user_agent=user_agent
            )

            user.last_login = datetime.now(timezone.utc)
            self.db.commit()

            logger.info("Token pair generated successfully", extra={"user_id": user.user_id})
            return Token(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer"
            )

        except Exception as e:
            logger.exception("Error generating token pair")
            raise HTTPException(status_code=500, detail="Failed to generate tokens")

    def refresh_access_token(self, refresh_token: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Token:
        try:
            logger.info("Refreshing access token", extra={"token": refresh_token[:10] + "..."})

            payload = self.utility.decode_token(refresh_token, required_token_type="REFRESH")
            username = payload.get("sub")

            token_record = self.db.query(AuthToken).filter(
                AuthToken.token == refresh_token,
                AuthToken.token_type == TokenType.REFRESH,
                AuthToken.revoked == False
            ).first()

            if not token_record or token_record.expires_at < datetime.now(timezone.utc):
                logger.warning("Invalid or expired refresh token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user = self.db.query(User).filter(User.username == username).first()
            if not user or not user.is_active:
                logger.warning("Invalid or inactive user", extra={"username": username})
                raise HTTPException(status_code=401, detail="Invalid user")

            token_record.revoked = True

            access_token, access_expire = self.utility.create_token(
                username=user.username,
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                token_type="ACCESS"
            )
            new_refresh_token, refresh_expire = self.utility.create_token(
                username=user.username,
                expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                token_type="REFRESH"
            )

            access_token_id, refresh_token_id = self.utility.store_tokens(
                db=self.db,
                user_id=user.user_id,
                access_token=access_token,
                refresh_token=new_refresh_token,
                access_expire=access_expire,
                refresh_expire=refresh_expire
            )
            self.utility.create_session(
                db=self.db,
                user_id=user.user_id,
                token_id=access_token_id,
                expires_at=access_expire,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.commit()

            logger.info("Access token refreshed successfully", extra={"user_id": user.user_id})
            return Token(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer"
            )

        except HTTPException as he:
            logger.error(f"HTTP error during token refresh: {he.detail}")
            raise
        except Exception as e:
            logger.exception("Unexpected error during token refresh")
            raise HTTPException(status_code=500, detail="Internal server error")

    def invalidate_refresh_token(self, jti: str) -> dict:
        """
        Invalidates a refresh token using its JTI (JWT ID).
        
        Args:
            jti (str): The JWT ID of the token to invalidate.
            
        Returns:
            dict: A dictionary containing the result message.
            
        Raises:
            HTTPException: If the token is not found or an error occurs.
        """
        try:
            logger.info("Invalidating refresh token", extra={"jti": jti})
            
            # Find the refresh token by JTI
            token_record = self.db.query(AuthToken).filter(
                AuthToken.token == jti,
                AuthToken.token_type == TokenType.REFRESH,
                AuthToken.revoked == False
            ).first()
            
            if not token_record:
                logger.warning("Refresh token not found for invalidation", extra={"jti": jti})
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Refresh token not found"
                )
            
            # Mark the token as revoked
            token_record.revoked = True
            token_record.expires_at = datetime.now(timezone.utc)
            
            # Also invalidate any associated sessions
            sessions = self.db.query(DBSession).filter(
                DBSession.user_id == token_record.user_id,
                DBSession.is_active == True
            ).all()
            
            for session in sessions:
                session.is_active = False
                session.expires_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            logger.info("Refresh token invalidated successfully", extra={
                "jti": jti,
                "user_id": token_record.user_id,
                "sessions_invalidated": len(sessions)
            })
            
            return {"message": "Refresh token invalidated successfully"}
            
        except HTTPException as he:
            logger.error(f"HTTP error during token invalidation: {he.detail}")
            raise
        except Exception as e:
            logger.exception("Unexpected error during token invalidation")
            raise HTTPException(status_code=500, detail="Internal server error")

    def invalidate_all_user_tokens(self, user_id: int) -> dict:
        """
        Invalidates all refresh tokens for a specific user.
        This is useful for "logout from all devices" functionality.
        
        Args:
            user_id (int): The ID of the user whose tokens should be invalidated.
            
        Returns:
            dict: A dictionary containing the result message and count of invalidated tokens.
            
        Raises:
            HTTPException: If the user is not found or an error occurs.
        """
        try:
            logger.info("Invalidating all user tokens", extra={"user_id": user_id})
            
            # Verify user exists
            user = self.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                logger.warning("User not found for token invalidation", extra={"user_id": user_id})
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Find all active refresh tokens for the user
            active_tokens = self.db.query(AuthToken).filter(
                AuthToken.user_id == user_id,
                AuthToken.token_type == TokenType.REFRESH,
                AuthToken.revoked == False
            ).all()
            
            # Mark all tokens as revoked
            tokens_count = len(active_tokens)
            for token in active_tokens:
                token.revoked = True
                token.expires_at = datetime.now(timezone.utc)
            
            # Invalidate all associated sessions
            sessions = self.db.query(DBSession).filter(
                DBSession.user_id == user_id,
                DBSession.is_active == True
            ).all()
            
            sessions_count = len(sessions)
            for session in sessions:
                session.is_active = False
                session.ended_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            logger.info("All user tokens invalidated successfully", extra={
                "user_id": user_id,
                "tokens_invalidated": tokens_count,
                "sessions_invalidated": sessions_count
            })
            
            return {
                "message": "All user tokens invalidated successfully",
                "tokens_invalidated": tokens_count,
                "sessions_invalidated": sessions_count
            }
            
        except HTTPException as he:
            logger.error(f"HTTP error during user token invalidation: {he.detail}")
            raise
        except Exception as e:
            logger.exception("Unexpected error during user token invalidation")
            raise HTTPException(status_code=500, detail="Internal server error")

    def request_password_reset(self, email: str) -> dict:
        try:
            logger.info("Initiating password reset", extra={"email": email})

            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                logger.warning("No user found with given email", extra={"email": email})
                raise HTTPException(status_code=404, detail="User not found")

            reset_token, reset_expire = self.utility.create_token(
                username=user.username,
                expires_delta=timedelta(hours=settings.RESET_TOKEN_EXPIRE_HOURS),
                token_type="RESET"
            )

            db_reset_token = PasswordResetToken(
                user_id=user.user_id,
                token=reset_token,
                expires_at=reset_expire,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(db_reset_token)
            self.db.commit()

            logger.info("Password reset token generated", extra={"user_id": user.user_id})
            return {"message": "Password reset token generated", "token": reset_token}

        except HTTPException as he:
            logger.error(f"HTTP error during password reset request: {he.detail}")
            raise
        except Exception as e:
            logger.exception("Unexpected error during password reset request")
            raise HTTPException(status_code=500, detail="Internal server error")

    def reset_password(self, token: str, new_password: str) -> dict:
        try:
            logger.info("Processing password reset", extra={"token": token[:10] + "..."})

            payload = self.utility.decode_token(token, required_token_type="RESET")
            username = payload.get("sub")

            reset_token = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.token == token,
                PasswordResetToken.used == False
            ).first()

            if not reset_token or reset_token.expires_at < datetime.now(timezone.utc):
                logger.warning("Invalid or expired password reset token")
                raise HTTPException(status_code=401, detail="Invalid or expired reset token")

            user = self.db.query(User).filter(User.user_id == reset_token.user_id).first()
            if not user:
                logger.warning("User not found for password reset", extra={"user_id": reset_token.user_id})
                raise HTTPException(status_code=404, detail="User not found")

            user.password_hash = self.utility.get_password_hash(new_password)
            reset_token.used = True
            self.db.commit()

            logger.info("Password reset successful", extra={"user_id": user.user_id})
            return {"message": "Password reset successful"}

        except HTTPException as he:
            logger.error(f"HTTP error during password reset: {he.detail}")
            raise
        except Exception as e:
            logger.exception("Unexpected error during password reset")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            logger.debug("Fetching user by email", extra={"email": email})
            return self.db.query(User).filter(User.email == email).first()
        except Exception as e:
            logger.exception("Error fetching user by email")
            raise HTTPException(status_code=500, detail="Internal server error")

    def validate_user_session(self, access_token: str) -> DBSession:
        """
        Validates a user session using the provided access token.

        Args:
            access_token (str): The access token to validate.

        Returns:
            DBSession: The validated session object.

        Raises:
            HTTPException: If the session is invalid or expired.
        """
        try:
            session = self.utility.validate_session(self.db, access_token)
            logger.info("Session validated successfully", extra={"user_id": session.user_id})
            return session
        except Exception as e:
            logger.error(f"Session validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
                headers={"WWW-Authenticate": "Bearer"}
            )

    def get_user_roles(self, user_id: int) -> List[Role]:
        """
        Retrieves all roles associated with a user.

        Args:
            user_id (int): The ID of the user whose roles are to be retrieved.

        Returns:
            List[Role]: A list of Role objects associated with the user.

        Raises:
            HTTPException: If the user is not found or an error occurs.
        """
        try:
            roles = self.utility.get_user_roles(self.db, user_id)
            logger.info(f"Retrieved roles for user_id: {user_id}")
            return roles
        except self.utility.UserNotFoundError:
            logger.error(f"User not found for role retrieval: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            logger.error(f"Failed to retrieve roles for user_id {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")