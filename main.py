from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routes.routers import router as api_router
from fastapi.staticfiles import StaticFiles
from routes.resume_screening_routes import initialize_embedding_model
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="HR Screening",
    description="API and UI for MG ChatB data processing and visualization",
    version="1.0.0"
)

# Enable CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI application")
    try:
        await initialize_embedding_model()
        logger.info("Embedding model initialization completed")
    except Exception as e:
        logger.error(f"Failed to initialize embedding model on startup: {str(e)}")
        raise


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)