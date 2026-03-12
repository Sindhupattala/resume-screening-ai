from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import io
import csv
import asyncio
from dotenv import load_dotenv
import os
import sys
 
# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
 
# Import custom services
from services.bot_services.resume_info_extractor import ResumeInfoExtractor
from services.bot_services.pdf_processor import PDFProcessor
from services.bot_services.llm_handler import LLMHandler
from services.bot_services.candidate_scorer import Candidate
from services.bot_services.cache_handler import CacheHandler
 
# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)
logger.info(f"Environment variables loaded: EMBEDDING_MODEL_NAME={os.getenv('DEPLOYMENT_EMB')}, "
            f"AZURE_SEARCH_ENDPOINT={os.getenv('AZURE_SEARCH_ENDPOINT')}")
 
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
 
# Pydantic models
class CandidateScore(BaseModel):
    name: str
    score: float
    reason: str
    individual_scores: Dict[str, Any] = Field(default_factory=dict)
 
class MatchingResult(BaseModel):
    success: bool
    message: str
    candidates: List[CandidateScore] = Field(default_factory=list)
    total_candidates: int = 0
    candidates_above_threshold: int = 0
 
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_details: Optional[str] = None
 
# Global variables
cache_handler = CacheHandler()
resume_info_extractor = ResumeInfoExtractor()
embedding_model = None
latest_output_rows = []
 
# Startup event to initialize embedding model
async def initialize_embedding_model():
    global embedding_model
    try:
        logger.info("Starting embedding model initialization")
        embedding_model = LLMHandler.get_embedding_model()
        logger.info(f"Embedding model initialized: type={type(embedding_model)}, value={embedding_model}")
        if embedding_model is None:
            logger.error("Embedding model is None")
            raise ValueError("Embedding model initialization returned None")
    except Exception as e:
        logger.error(f"Failed to initialize embedding model: {str(e)}")
        raise
 
# Controller class
class ResumeScreeningController:
    def __init__(self, router: APIRouter):
        self.router = router
        self.register_routes()
 
    @staticmethod
    async def convert_uploadfile_to_filelike(upload_file: UploadFile):
        try:
            await upload_file.seek(0)
            content = await upload_file.read()
            file_obj = io.BytesIO(content)
            file_obj.name = upload_file.filename
            logger.info(f"Converted upload file: {upload_file.filename}")
            return file_obj
        except Exception as e:
            logger.error(f"Failed to convert upload file {upload_file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to process file {upload_file.filename}: {str(e)}")
 
    @staticmethod
    async def convert_multiple_uploadfiles(upload_files: List[UploadFile]):
        converted_files = []
        for upload_file in upload_files:
            file_obj = await ResumeScreeningController.convert_uploadfile_to_filelike(upload_file)
            converted_files.append(file_obj)
        return converted_files
 
    async def process_single_candidate(
        self,
        name: str,
        candidate_documents: List,
        query: str,
        threshold: float
    ) -> Optional[CandidateScore]:
        try:
            logger.info(f"Processing candidate: {name}")
            logger.info(f"Embedding model status: {embedding_model}")
            qa_chain = LLMHandler.create_qa_chain_with_scoring(
                candidate_documents, embedding_model, name
            )
            if not qa_chain:
                logger.warning(f"Failed to create QA chain for candidate: {name}")
                return None
            if not hasattr(qa_chain, 'invoke'):
                logger.error(f"Invalid QA chain for candidate {name}: missing invoke method")
                return None
            resume_text = "\n".join(doc.page_content for doc in candidate_documents)
            cached_score = cache_handler.get_cached_result(query, resume_text)
            if cached_score:
                score = cached_score
                logger.info(f"Using cached score for candidate: {name}, Mandatory Skills: {score['individual_scores'].get('Mandatory Skills', '0.0/50')}")
            else:
                logger.info(f"Analyzing candidate: {name}")
                score = Candidate.analyze_candidate(qa_chain, query, name, resume_text)
                cache_handler.store_result(query, resume_text, score)
            # Check if candidate is shortlisted based on Mandatory Skills score > 30
            if score.get("shortlisted", False):
                logger.info(f"Candidate {name} shortlisted with Mandatory Skills score: {score['individual_scores'].get('Mandatory Skills', '0.0/50')}, Total score: {score['rating']}")
                return CandidateScore(
                    name=name,
                    score=score["rating"],
                    reason=score["reason"],
                    individual_scores=score.get("individual_scores", {})
                )
            logger.info(f"Candidate {name} not shortlisted: Mandatory Skills score {score['individual_scores'].get('Mandatory Skills', '0.0/50')} <= 30")
            return None
        except Exception as e:
            logger.error(f"Error processing candidate {name}: {str(e)}")
            return None
 
    def register_routes(self):
        self.router.add_api_route(
            "/api/health",
            self.health_check,
            methods=["GET"],
            tags=["Health"],
            summary="Health check",
            description="Performs a health check on the API"
        )
        self.router.add_api_route(
            "/api/match-candidates",
            self.match_candidates,
            methods=["POST"],
            response_model=MatchingResult,
            tags=["Candidates"],
            summary="Match candidates",
            description="Match candidates against a job description provided as text"
        )
        self.router.add_api_route(
            "/api/match-candidates-with-jd-file",
            self.match_candidates_with_jd_file,
            methods=["POST"],
            response_model=MatchingResult,
            tags=["Candidates"],
            summary="Match candidates with JD file",
            description="Match candidates against a job description provided as a file"
        )
        self.router.add_api_route(
            "/api/clear-cache",
            self.clear_cache,
            methods=["POST"],
            tags=["Cache"],
            summary="Clear cache",
            description="Clears the cache"
        )
        self.router.add_api_route(
            "/api/download-shortlisted",
            self.download_shortlisted,
            methods=["GET"],
            response_class=StreamingResponse,
            tags=["Candidates"],
            summary="Download shortlisted candidates",
            description="Downloads a CSV of shortlisted candidates"
        )
 
    async def health_check(self):
        try:
            logger.info("Performing health check")
            return {
                "status": "healthy",
                "embedding_model_loaded": embedding_model is not None,
                "cache_handler_ready": cache_handler is not None
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
 
    async def match_candidates(
        self,
        background_tasks: BackgroundTasks,
        job_description: str = Form(...),
        threshold: float = Form(10.0),
        resume_files: List[UploadFile] = File(...)
    ):
        try:
            logger.info("Starting candidate matching process")
            if not job_description.strip():
                logger.error("Job description is empty")
                raise HTTPException(status_code=400, detail="Job description cannot be empty")
            if not resume_files:
                logger.error("No resume files provided")
                raise HTTPException(status_code=400, detail="At least one resume file must be uploaded")
            allowed_types = {"pdf", "docx"}
            for file in resume_files:
                if not file.filename:
                    logger.error("Resume file missing filename")
                    raise HTTPException(status_code=400, detail="All files must have filenames")
                file_extension = file.filename.split(".")[-1].lower()
                if file_extension not in allowed_types:
                    logger.error(f"Unsupported file format: {file.filename}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {file.filename} has unsupported format. Only PDF and DOCX are allowed"
                    )
            logger.info(f"Processing {len(resume_files)} resume files")
            converted_files = await self.convert_multiple_uploadfiles(resume_files)
            logger.info("Converting files to documents with metadata")
            try:
                documents_with_metadata = PDFProcessor.process_multiple_documents(converted_files)
            except Exception as e:
                logger.error(f"PDFProcessor failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error processing documents: {str(e)}")
            if not documents_with_metadata:
                logger.error("No text extracted from uploaded files")
                raise HTTPException(status_code=400, detail="No text found in the uploaded files")
            candidate_names = list(set(
                doc.metadata.get('candidate_name', 'Unknown') for doc in documents_with_metadata
            ))
            logger.info(f"Found {len(candidate_names)} unique candidates")
            tasks = []
            for name in candidate_names:
                candidate_documents = [
                    doc for doc in documents_with_metadata
                    if doc.metadata.get('candidate_name') == name
                ]
                tasks.append(self.process_single_candidate(name, candidate_documents, job_description, threshold))
            logger.info("Processing candidates concurrently")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_candidates = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed with exception: {str(result)}")
                    continue
                if result is not None:
                    successful_candidates.append(result)
            ranked_candidates = sorted(successful_candidates, key=lambda x: x.score, reverse=True)
            logger.info(f"Successfully processed {len(ranked_candidates)} candidates shortlisted based on Mandatory Skills score > 30")
            global latest_output_rows
            output_rows = []
            for candidate in ranked_candidates:
                candidate_docs = [
                    doc for doc in documents_with_metadata
                    if doc.metadata.get('candidate_name') == candidate.name
                ]
                resume_text = "\n".join(doc.page_content for doc in candidate_docs)
                try:
                    personal_info = resume_info_extractor.extract_info(resume_text, candidate.name)
                except Exception as e:
                    logger.error(f"Failed to extract personal info for {candidate.name}: {str(e)}")
                    personal_info = {}
                row = {
                    "Candidate Name": candidate.name,
                    "Score": candidate.score,
                    "Reason": candidate.reason,
                    "Mandatory Skills": candidate.individual_scores.get("Mandatory Skills", "0.0/50"),
                    **personal_info
                }
                output_rows.append(row)
            latest_output_rows = output_rows  # Reset to avoid accumulating old data
            logger.info(f"Stored {len(output_rows)} candidates in latest_output_rows")
            return MatchingResult(
                success=True,
                message=f"Successfully processed {len(candidate_names)} candidates. {len(ranked_candidates)} candidates shortlisted based on Mandatory Skills score > 30",
                candidates=ranked_candidates,
                total_candidates=len(candidate_names),
                candidates_above_threshold=len(ranked_candidates)
            )
        except HTTPException as he:
            logger.error(f"HTTP error in match_candidates: {he.detail}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in match_candidates: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to process candidates: {str(e)}")
 
    async def match_candidates_with_jd_file(
        self,
        background_tasks: BackgroundTasks,
        job_description_file: UploadFile = File(...),
        threshold: float = Form(10.0),
        resume_files: List[UploadFile] = File(...)
    ):
        try:
            logger.info("Starting candidate matching with JD file")
            if not job_description_file.filename:
                logger.error("Job description file missing filename")
                raise HTTPException(status_code=400, detail="Job description file must have a filename")
            jd_file_extension = job_description_file.filename.split(".")[-1].lower()
            if jd_file_extension not in {"pdf", "docx"}:
                logger.error(f"Unsupported job description file format: {job_description_file.filename}")
                raise HTTPException(
                    status_code=400,
                    detail="Job description file must be PDF or DOCX format"
                )
            logger.info(f"Processing job description file: {job_description_file.filename}")
            jd_file_obj = await self.convert_uploadfile_to_filelike(job_description_file)
            try:
                job_description = PDFProcessor.extract_text_from_file(jd_file_obj)
            except Exception as e:
                logger.error(f"Failed to extract text from job description file: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error processing job description file: {str(e)}")
            if not job_description.strip():
                logger.error("Job description file is empty")
                raise HTTPException(status_code=400, detail="Job description file appears to be empty")
            logger.info("Calling match_candidates with extracted job description")
            return await self.match_candidates(
                background_tasks=background_tasks,
                job_description=job_description,
                threshold=threshold,
                resume_files=resume_files
            )
        except HTTPException as he:
            logger.error(f"HTTP error in match_candidates_with_jd_file: {he.detail}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in match_candidates_with_jd_file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to process candidates: {str(e)}")
 
    async def clear_cache(self):
        try:
            logger.info("Clearing cache")
            if hasattr(cache_handler, 'clear'):
                cache_handler.clear()
                logger.info("Cache cleared successfully")
                return {"success": True, "message": "Cache cleared successfully"}
            else:
                logger.error("CacheHandler does not support clearing")
                raise HTTPException(status_code=500, detail="CacheHandler does not support clearing")
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")
 
    async def download_shortlisted(self):
        try:
            logger.info("Attempting to download shortlisted candidates")
            global latest_output_rows
            if not latest_output_rows:
                logger.error("No shortlisted candidates found")
                raise HTTPException(status_code=404, detail="No shortlisted candidates")
            logger.info(f"Generating CSV for {len(latest_output_rows)} candidates")
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=latest_output_rows[0].keys())
            writer.writeheader()
            writer.writerows(latest_output_rows)
            output.seek(0)
            logger.info("CSV generated successfully")
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=shortlisted_candidates.csv"}
            )
        except HTTPException as he:
            logger.error(f"HTTP error in download_shortlisted: {he.detail}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in download_shortlisted: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to download shortlisted candidates: {str(e)}")