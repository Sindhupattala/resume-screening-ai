from urllib.parse import quote_plus
from dotenv import load_dotenv
import os
from typing import Optional, Dict
from dataclasses import dataclass

load_dotenv()

class SettingsError(Exception):
    """Custom exception for settings configuration errors"""
    pass

@dataclass
class Settings:
    """Class to manage application settings with robust configuration handling"""
    
    # Database settings
    SERVER: str
    DATABASE: str
    USERNAME: str
    PASSWORD: str
    DATABASE_URL: str
    
    # Authentication settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_TOKEN_EXPIRE_HOURS:int = 4
    
    # Azure OpenAI settings
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = None
    AZURE_OPENAI_BASE_URL: Optional[str] = None

    def __init__(self):
        """Initialize settings with environment variable validation and URL construction"""
        try:
            # Required environment variables
            required_vars = {
                "SERVER": "server",
                "DATABASE": "database",
                "PYODBC_USERNAME": "username",
                "PASSWORD": "password",
                "SECRET_KEY": "secret key"
            }
            
            # Validate required variables
            env_values = {}
            for env_var, name in required_vars.items():
                value = os.getenv(env_var)
                if not value:
                    raise SettingsError(f"Missing required environment variable: {name} ({env_var})")
                env_values[name] = value
                # print(value)
            
            # Set required attributes
            self.SERVER = env_values["server"]
            self.DATABASE = env_values["database"]
            self.USERNAME = env_values["username"]
            self.PASSWORD = env_values["password"]
            self.SECRET_KEY = env_values["secret key"]
            
            # Set optional attributes with defaults
            self.ALGORITHM = os.getenv("ALGORITHM", self.ALGORITHM)
            self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 
                                                          self.ACCESS_TOKEN_EXPIRE_MINUTES))
            self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 
                                                        self.REFRESH_TOKEN_EXPIRE_DAYS))
            self.RESET_TOKEN_EXPIRE_HOURS=int(os.getenv("RESET_TOKEN_EXPIRE_HOURS", 
                                                        self.RESET_TOKEN_EXPIRE_HOURS))
            
            # Set Azure OpenAI attributes
            self.AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            self.AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
            self.AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
            self.AZURE_OPENAI_BASE_URL = os.getenv("AZURE_OPENAI_BASE_URL")

            # Encode credentials and construct DATABASE_URL
            self._construct_database_url()
            
        except ValueError as e:
            raise SettingsError(f"Invalid value in environment variable: {str(e)}")
        except Exception as e:
            raise SettingsError(f"Unexpected error initializing settings: {str(e)}")

    def _construct_database_url(self) -> None:
        """Constructs the database URL with encoded credentials"""
        try:
            encoded_password = quote_plus(self.PASSWORD)
            encoded_server = quote_plus(self.SERVER)
            encoded_database = quote_plus(self.DATABASE)
            encoded_username = quote_plus(self.USERNAME)
            
            self.DATABASE_URL = (
                f"mssql+pyodbc://{encoded_username}:{encoded_password}@{encoded_server}/{encoded_database}"
                "?driver=ODBC+Driver+18+for+SQL+Server"
                "&Encrypt=yes"
                "&TrustServerCertificate=no"
                "&ConnectionTimeout=30"
                "&MARS_Connection=Yes"
            )
        except Exception as e:
            raise SettingsError(f"Failed to construct database URL: {str(e)}")

# Singleton instance
settings = Settings()