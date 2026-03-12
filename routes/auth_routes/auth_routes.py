from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Annotated
import re

from schemas.auth_schemas import UserCreate, UserResponse, Token, PasswordResetRequest, PasswordReset
from services.auth_services.auth_services import AuthService
from services.auth_services.utils import UtilityFunctions
from db.session import get_db
from services.auth_services.current_user_services import CurrentUser
from core.logging import TimeZoneLogger

logger= TimeZoneLogger().get_logger()


class AuthController:
    def __init__(self, router: APIRouter):
        """
        Initialize AuthController with proper route registration
        """
        # Register routes using add_api_route for better control
        self.router = router
        self.router.add_api_route(
            '/auth/signup',
            self.signup,
            methods=['POST'],
            tags=['Authentication'],
            response_model=UserResponse,
            summary="User Registration",
            description="Register a new user account"
        )
        
        self.router.add_api_route(
            '/auth/login',
            self.login,
            methods=['POST'],
            tags=['Authentication'],
            response_model=Token,
            summary="User Login",
            description="Authenticate user and return access token"
        )
        
        self.router.add_api_route(
            '/auth/logout',
            self.logout,
            methods=['POST'],
            tags=['Authentication'],
            summary="User Logout",
            description="Logout user and invalidate refresh token"
        )
        
        self.router.add_api_route(
            '/auth/refresh',
            self.refresh_token,
            methods=['POST'],
            tags=['Authentication'],
            response_model=Token,
            summary="Refresh Token",
            description="Refresh access token using refresh token"
        )
        
        self.router.add_api_route(
            '/auth/password/reset/request',
            self.request_password_reset,
            methods=['POST'],
            tags=['Authentication'],
            summary="Request Password Reset",
            description="Request password reset email"
        )
        
        self.router.add_api_route(
            '/auth/password/reset',
            self.reset_password,
            methods=['POST'],
            tags=['Authentication'],
            summary="Reset Password",
            description="Reset password using reset token"
        )
        
        self.router.add_api_route(
            '/auth/users/me',
            self.read_users_me,
            methods=['GET'],
            tags=['Authentication'],
            response_model=UserResponse,
            summary="Get Current User",
            description="Get current authenticated user information"
        )

    async def signup(self, user: UserCreate, db: Session = Depends(get_db)):
        """
        User signup endpoint with comprehensive error handling
        """
        try:
            logger.info(f"Attempting user signup for email: {user.email}")
            
            # Validate input
            if not user.email or not user.password:
                logger.warning("Signup attempt with missing email or password")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email and password are required"
                )
            
            # Validate email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, user.email):
                logger.warning(f"Invalid email format: {user.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
            
            # Validate password strength
            if len(user.password) < 8:
                logger.warning("Signup attempt with weak password")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password must be at least 8 characters long"
                )
            
            # Create auth service instance
            auth_service = AuthService(db)
            
            # Check if user already exists
            existing_user = auth_service.get_user_by_email(user.email)
            if existing_user:
                logger.warning(f"Signup attempt with existing email: {user.email}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists"
                )
            
            # Create user
            db_user = auth_service.create_user(user)
            roles = auth_service.get_user_roles(db_user.user_id)
            
            logger.info(f"User created successfully: {db_user.user_id}")
            return UserResponse(
                user_id=db_user.user_id,
                username=db_user.username, 
                email=db_user.email,
                first_name=db_user.first_name,
                last_name=db_user.last_name,
                is_active=db_user.is_active,
                roles=roles
                )
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error during signup: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during signup"
            )
        except Exception as e:
            logger.error(f"Unexpected error during signup: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during signup"
            )

    async def login(self, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
        """
        User login endpoint with enhanced security and error handling
        """
        try:
            logger.info(f"Login attempt for username: {form_data.username}")
            
            # Validate input
            if not form_data.username or not form_data.password:
                logger.warning("Login attempt with missing username or password")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username and password are required"
                )
            
            # Create utility instance with db
            utility = UtilityFunctions()
            user = utility.authenticate_user(db,form_data.username, form_data.password)
            
            if not user:
                logger.warning(f"Failed login attempt for username: {form_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Create token pair
            auth_service = AuthService(db)
            token_pair = auth_service.create_token_pair(user)
            
            logger.info(f"User logged in successfully: {user.user_id}")
            return token_pair
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error during login: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during login"
            )
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during login"
            )
        
        

    async def logout(self, current_user: Annotated[tuple, Depends(CurrentUser)], db: Session = Depends(get_db)):
        """
        User logout endpoint with token invalidation
        """
        try:
            logger.info("Logout attempt")
            # print(current_user())
            
            # Validate current user
            if not current_user() or len(current_user()) != 2:
                logger.error("Invalid current user data structure during logout")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user authentication data"
                )
            
            user, token_data = current_user()
            
            
            if not user:
                logger.error("No user data found during logout")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            if not token_data or not hasattr(token_data, 'jti'):
                logger.error("No token data or JTI found during logout")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token data"
                )
            
            # Create auth service instance
            auth_service = AuthService(db)


   
            # Invalidate the refresh token using JTI from token data
            result = auth_service.invalidate_refresh_token(token_data.jti)
            
            logger.info(f"User logged out successfully: {user.user_id}")
            return {"message": "Successfully logged out"}
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error during logout: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during logout"
            )
        except Exception as e:
            logger.error(f"Unexpected error during logout: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during logout"
            )

    async def refresh_token(self, refresh_token: str, db: Session = Depends(get_db)):
        """
        Refresh access token endpoint with validation
        """
        try:
            logger.info("Token refresh attempt")
            
            # Validate input
            if not refresh_token or not refresh_token.strip():
                logger.warning("Token refresh attempt with empty token")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Refresh token is required"
                )
            
            auth_service = AuthService(db)
            new_token_pair =auth_service.refresh_access_token(refresh_token)
            
            logger.info("Token refreshed successfully")
            return new_token_pair
            
        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error during token refresh: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during token refresh"
            )
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during token refresh"
            )

    async def request_password_reset(self, reset_request: PasswordResetRequest, db: Session = Depends(get_db)):
        """
        Request password reset endpoint with validation
        """
        try:
            logger.info(f"Password reset request for email: {reset_request.email}")
            
            # Validate input
            if not reset_request.email or not reset_request.email.strip():
                logger.warning("Password reset request with empty email")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email is required"
                )
            
            # Validate email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, reset_request.email):
                logger.warning(f"Invalid email format: {reset_request.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
            
            auth_service = AuthService(db)
            result = await auth_service.request_password_reset(reset_request.email)
            
            logger.info(f"Password reset request processed for email: {reset_request.email}")
            return result
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error during password reset request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during password reset request"
            )
        except Exception as e:
            logger.error(f"Unexpected error during password reset request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during password reset request"
            )

    async def reset_password(self, reset_data: PasswordReset, db: Session = Depends(get_db)):
        """
        Reset password endpoint with validation
        """
        try:
            logger.info("Password reset attempt")
            
            # Validate input
            if not reset_data.token or not reset_data.token.strip():
                logger.warning("Password reset attempt with empty token")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reset token is required"
                )
            
            if not reset_data.new_password or len(reset_data.new_password) < 8:
                logger.warning("Password reset attempt with weak password")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password must be at least 8 characters long"
                )
            
            auth_service = AuthService(db)
            result = await auth_service.reset_password(reset_data.token, reset_data.new_password)
            
            logger.info("Password reset completed successfully")
            return result
            
        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Invalid reset token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired reset token"
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error during password reset: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during password reset"
            )
        except Exception as e:
            logger.error(f"Unexpected error during password reset: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during password reset"
            )

    async def read_users_me(self, current_user: Annotated[tuple, Depends(CurrentUser)]):
        """
        Get current user information endpoint with validation
        """
        try:
            logger.info("User profile request")
            
            # Validate current user
            if not current_user or len(current_user) != 2:
                logger.error("Invalid current user data structure")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user authentication data"
                )
            
            user, token_data = current_user
            
            if not user:
                logger.error("No user data found in authentication")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            if not token_data or not hasattr(token_data, 'roles'):
                logger.error("No token data or roles found in authentication")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token data"
                )
            
            logger.info(f"User profile retrieved successfully: {user.user_id}")
            return UserResponse(**user.__dict__, roles=token_data.roles)
            
        except HTTPException:
            raise
        except AttributeError as e:
            logger.error(f"Attribute error in user profile: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing user data"
            )
        except Exception as e:
            logger.error(f"Unexpected error in user profile: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while retrieving user profile"
            )