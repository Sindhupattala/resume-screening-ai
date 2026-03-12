from passlib.context import CryptContext
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import jwt
import logging
from typing import Optional, Dict, Any, List

# --- Local Imports ---
from core.config import settings
from db.models.auth_models import User, AuthToken, Session as DBSession, TokenType, Role
from core.logging import TimeZoneLogger

logger = TimeZoneLogger().get_logger()

# --- Password Context ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Custom Exceptions ---
class AuthError(Exception):
    """Base class for all auth-related errors."""
    def __init__(self, message: str = "Authentication Error", detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(message)

class InvalidTokenError(AuthError):
    pass

class ExpiredTokenError(AuthError):
    pass

class TokenDecodeError(AuthError):
    pass

class UserNotFoundError(AuthError):
    pass

class PasswordMismatchError(AuthError):
    pass

class InvalidSessionError(AuthError):
    pass

class UtilityFunctions:
    def __init__(self):
        self.pwd_context = pwd_context
        logger.info("UtilityFunctions initialized with bcrypt context.")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifies a plain password against a hashed one.
        """
        try:
            if not self.pwd_context.verify(plain_password, hashed_password):
                logger.warning("Password mismatch.")
                raise PasswordMismatchError(message="Incorrect password.")
            return True
        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}")
            raise

    def get_password_hash(self, password: str) -> str:
        """
        Returns a hash of the given password.
        """
        try:
            return self.pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Failed to generate password hash: {str(e)}")
            raise

    def create_token(self, username: str, expires_delta: timedelta, token_type: str) -> tuple:
        """
        Generates a JWT token with dynamic expiration and token type for a given username.
        
        Args:
            username (str): The username to encode in the token.
            expires_delta (timedelta): The duration until the token expires.
            token_type (str): The type of token (e.g., ACCESS, REFRESH, RESET).
        
        Returns:
            tuple: A tuple containing the encoded JWT token and its expiration datetime.
        """
        try:
            to_encode = {"sub": username}
            expire = datetime.now(timezone.utc) + expires_delta
            to_encode.update({"exp": expire, "type": token_type})
            encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
            logger.info(f"{token_type.capitalize()} token created successfully for user: {username}")
            return encoded_jwt, expire
        except Exception as e:
            logger.error(f"Token creation failed for user {username}: {str(e)}")
            raise

    def decode_token(self, token: str, required_token_type: Optional[str] = None) -> dict:
        """
        Decodes and validates a JWT token.

        Raises appropriate exceptions if token is invalid or expired.
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            exp = payload.get("exp")
            token_type = payload.get("type")

            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                logger.warning("Token has expired.")
                raise ExpiredTokenError(message="Token has expired.")

            if required_token_type and token_type != required_token_type:
                logger.warning(f"Invalid token type: expected '{required_token_type}', got '{token_type}'")
                raise InvalidTokenError(message=f"Invalid token type: {token_type}")

            return payload
        except jwt.ExpiredSignatureError:
            logger.error("Expired token signature detected.")
            raise ExpiredTokenError(message="Token has expired.")
        except jwt.DecodeError:
            logger.error("JWT DecodeError: Invalid token.")
            raise TokenDecodeError(message="Could not decode token.")
        except jwt.PyJWTError as e:
            logger.error(f"JWT error during decoding: {str(e)}")
            raise TokenDecodeError(message="Invalid token.")

    def authenticate_user(self, db: Session, username: str, password: str) -> User:
        """
        Authenticates a user by username and password.
        Returns the user object if successful, raises an error otherwise.
        """
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                logger.warning(f"User not found: {username}")
                raise UserNotFoundError(message="User not found.")
            if not self.verify_password(password, user.password_hash):
                logger.warning(f"Password verification failed for user: {username}")
                raise PasswordMismatchError(message="Incorrect password.")
            logger.info(f"User authenticated: {username}")
            return user
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise

    def store_tokens(self, db: Session, user_id: int, access_token: str, refresh_token: str, access_expire: datetime, refresh_expire: datetime) -> tuple:
        """
        Stores access and refresh tokens in the database and returns their token IDs.

        Args:
            db (Session): The database session.
            user_id (int): The ID of the user associated with the tokens.
            access_token (str): The access token to store.
            refresh_token (str): The refresh token to store.
            access_expire (datetime): The expiration time of the access token.
            refresh_expire (datetime): The expiration time of the refresh token.

        Returns:
            tuple: A tuple containing the access token ID and refresh token ID.
        """
        try:
            # Store access token
            db_access_token = AuthToken(
                user_id=user_id,
                token=access_token,
                token_type=TokenType.ACCESS,
                expires_at=access_expire,
                revoked=False,
                created_at=datetime.now(timezone.utc)
            )
            # Store refresh token
            db_refresh_token = AuthToken(
                user_id=user_id,
                token=refresh_token,
                token_type=TokenType.REFRESH,
                expires_at=refresh_expire,
                revoked=False,
                created_at=datetime.now(timezone.utc)
            )
            db.add(db_access_token)
            db.add(db_refresh_token)
            db.flush()  # Ensure token_ids are generated
            logger.info(f"Tokens stored successfully for user_id: {user_id}")
            return db_access_token.token_id, db_refresh_token.token_id
        except Exception as e:
            logger.error(f"Failed to store tokens for user_id {user_id}: {str(e)}")
            raise

    def create_session(self, db: Session, user_id: int, token_id: int, expires_at: datetime, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> DBSession:
        """
        Creates a new session in the database for the given user and token ID.

        Args:
            db (Session): The database session.
            user_id (int): The ID of the user associated with the session.
            token_id (int): The ID of the access token associated with the session.
            expires_at (datetime): The expiration time of the session.
            ip_address (Optional[str]): The IP address of the client.
            user_agent (Optional[str]): The user agent of the client.

        Returns:
            DBSession: The created session object.
        """
        try:
            db_session = DBSession(
                user_id=user_id,
                token_id=token_id,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc),
                last_accessed=datetime.now(timezone.utc),
                expires_at=expires_at
            )
            db.add(db_session)
            logger.info(f"Session created successfully for user_id: {user_id}, token_id: {token_id}")
            return db_session
        except Exception as e:
            logger.error(f"Failed to create session for user_id {user_id}: {str(e)}")
            raise

    def validate_session(self, db: Session, access_token: str) -> DBSession:
        """
        Validates a session by checking the access token and its associated token ID.

        Args:
            db (Session): The database session.
            access_token (str): The access token to validate.

        Returns:
            DBSession: The valid session object.

        Raises:
            InvalidSessionError: If the session is invalid, expired, or not found.
        """
        try:
            # First, verify the token
            payload = self.decode_token(access_token, required_token_type="ACCESS")
            username = payload.get("sub")

            # Find the token in AuthToken table
            auth_token = db.query(AuthToken).filter(
                AuthToken.token == access_token,
                AuthToken.token_type == TokenType.ACCESS,
                AuthToken.revoked == False
            ).first()

            if not auth_token or auth_token.expires_at < datetime.now(timezone.utc):
                logger.warning(f"Invalid or expired access token: {access_token[:10]}...")
                raise InvalidSessionError(message="Invalid or expired access token.")

            # Find the session linked to the token_id
            session = db.query(DBSession).filter(
                DBSession.token_id == auth_token.token_id,
                DBSession.expires_at > datetime.now(timezone.utc)
            ).first()

            if not session:
                logger.warning(f"No active session found for token_id: {auth_token.token_id}")
                raise InvalidSessionError(message="Session not found or expired.")

            # Update last_accessed timestamp
            session.last_accessed = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"Session validated successfully for user_id: {session.user_id}")
            return session
        except InvalidTokenError as e:
            logger.error(f"Invalid token during session validation: {str(e)}")
            raise InvalidSessionError(message="Invalid token.")
        except ExpiredTokenError as e:
            logger.error(f"Expired token during session validation: {str(e)}")
            raise InvalidSessionError(message="Session token has expired.")
        except Exception as e:
            logger.error(f"Failed to validate session for token {access_token[:10]}...: {str(e)}")
            raise InvalidSessionError(message="Invalid session.")

    def get_user_roles(self, db: Session, user_id: int) -> List[Role]:
        """
        Retrieves all roles associated with a user.

        Args:
            db (Session): The database session.
            user_id (int): The ID of the user whose roles are to be retrieved.

        Returns:
            List[Role]: A list of Role objects associated with the user.

        Raises:
            UserNotFoundError: If the user does not exist.
        """
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                logger.warning(f"User not found: {user_id}")
                raise UserNotFoundError(message="User not found.")

            roles = user.roles  # Leverage the relationship defined in the User model
            logger.info(f"Retrieved {len(roles)} roles for user_id: {user_id}")
            return roles
        except Exception as e:
            logger.error(f"Failed to retrieve roles for user_id {user_id}: {str(e)}")
            raise