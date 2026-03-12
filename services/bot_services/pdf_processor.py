import os
import tempfile
import re
from typing import List, Dict
import PyPDF2
import docx  # Needed for reading DOCX files
from tempfile import NamedTemporaryFile

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader



class PDFProcessor:

    @staticmethod
    def extract_text_from_file(file):
        """Extract text from a PDF or DOCX file."""
        ext = os.path.splitext(file.name)[-1].lower()
        text = ""

        if ext == ".pdf":
            file.seek(0)
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text

        elif ext == ".docx":
            with NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
                file.seek(0)
                temp_file.write(file.read())
                temp_file_path = temp_file.name

            try:
                doc = docx.Document(temp_file_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            finally:
                os.remove(temp_file_path)

        else:
            raise ValueError("Unsupported file type. Only PDF and DOCX are supported.")

        return text

    @staticmethod
    def process_file(file):
        """Process the uploaded PDF or DOCX file and return LangChain documents."""
        ext = os.path.splitext(file.name)[-1].lower()

        if ext not in [".pdf", ".docx"]:
            raise ValueError("Unsupported file type. Only PDF and DOCX are allowed.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            file.seek(0)
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        try:
            if ext == ".pdf":
                loader = PyPDFLoader(temp_file_path)
            elif ext == ".docx":
                loader = Docx2txtLoader(temp_file_path)

            documents = loader.load()
            return documents

        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    @staticmethod    
    def process_multiple_documents(files) -> List[Dict]:
        """Process multiple PDF and DOCX files and return a list of documents with metadata."""
        documents_with_metadata = []

        for file in files:
            suffix = os.path.splitext(file.name)[-1].lower()

            if suffix not in ['.pdf', '.docx']:
                print(f"Skipping unsupported file format: {file.name}")
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                file.seek(0)
                temp_file.write(file.read())
                temp_file_path = temp_file.name

            try:
                if suffix == '.pdf':
                    loader = PyPDFLoader(temp_file_path)
                elif suffix == '.docx':
                    loader = Docx2txtLoader(temp_file_path)
                else:
                    continue

                documents = loader.load()
                extracted_text = "".join([doc.page_content for doc in documents])

                # candidate_email = EmailSender.extract_email_from_text(extracted_text)
                candidate_name = file.name.rsplit('.', 1)[0]  # remove extension

                for doc in documents:
                    doc.metadata['candidate_name'] = candidate_name
                    # doc.metadata['candidate_email'] = candidate_email

                documents_with_metadata.extend(documents)
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        return documents_with_metadata
