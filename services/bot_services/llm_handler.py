import os
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain_openai import AzureChatOpenAI
from langchain_openai import AzureOpenAIEmbeddings
# from langchain_community.vectorstores.azure_ai_search import AzureAISearchVectorStore
from langchain_community.vectorstores.azuresearch import AzureSearch
# Import from your cache handler class
# from Services.cache_handler import CacheHandler

from services.bot_services.cache_handler import CacheHandler

class LLMHandler:
    @staticmethod
    def init_llm():
        """Initialize the Azure LLM model."""
        return AzureChatOpenAI(
            api_version=os.getenv("API_VERSION"),
            azure_endpoint=os.getenv("ENDPOINT"),
            api_key=os.getenv("API_KEY"),
            model_name="gpt-4o-mini",
            temperature=0
        )

    @staticmethod
    def get_embedding_model():
        """Initialize and return the OpenAI embedding model for Azure."""
        return AzureOpenAIEmbeddings(
            deployment=os.getenv("DEPLOYMENT_EMB"),     # "text-embedding-3-small"
            model="text-embedding-3-small",             # Changed to match your deployment
            chunk_size=1,
            api_key=os.getenv("API_KEY"),               # Fixed: was openai_api_key
            azure_endpoint=os.getenv("ENDPOINT"),       # Fixed: was openai_api_base
            api_version=os.getenv("API_VERSION")        # Fixed: was openai_api_version
            # Removed: openai_api_type="azure" - not needed for AzureOpenAIEmbeddings
        )

    @staticmethod
    def get_text_splitter():
        """Return a text splitter using TikToken."""
        encoding = tiktoken.get_encoding("cl100k_base")
        return RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", " ", ""],
            length_function=lambda x: len(encoding.encode(x))
        )

    @staticmethod
    def create_qa_chain(documents, embedding_model):
        """Create a RetrievalQA chain using Azure AI Search."""
        
        text_splitter = LLMHandler.get_text_splitter()
        splits = text_splitter.split_documents(documents)

        if not splits:
            return None

        # Connect to Azure AI Search
        azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        azure_search_key = os.getenv("AZURE_SEARCH_KEY")
        azure_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

        vectorstore = AzureSearch(
            azure_search_endpoint=azure_search_endpoint,
            azure_search_key=azure_search_key,
            index_name=azure_search_index_name,
            embedding_function=embedding_model
        )

        # Upload documents with embeddings
        vectorstore.add_documents(splits)

        return RetrievalQA.from_chain_type(
            llm=LLMHandler.init_llm(),
            retriever=vectorstore.as_retriever()
        )

    @staticmethod
    def create_qa_chain_with_scoring(documents, embedding_model, candidate_name=None):
        """Create a QA chain with scoring using Azure AI Search."""

        if candidate_name:
            documents = [
                doc for doc in documents
                if doc.metadata.get("candidate_name") == candidate_name
            ]

        text_splitter = LLMHandler.get_text_splitter()
        splits = text_splitter.split_documents(documents)

        if not splits:
            return None

        azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        azure_search_key = os.getenv("AZURE_SEARCH_KEY")
        azure_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

        vectorstore = AzureSearch(
            azure_search_endpoint=azure_search_endpoint,
            azure_search_key=azure_search_key,
            index_name=azure_search_index_name,
            embedding_function=embedding_model
        )

        # Upload resume chunks with embedding into index
        vectorstore.add_documents(splits)

        return RetrievalQA.from_chain_type(
            llm=LLMHandler.init_llm(),
            retriever=vectorstore.as_retriever(),  # search_kwargs={"k": 5}
            return_source_documents=True
        )

    @staticmethod
    def get_resume_score_with_cache(jd_text, resume_text):
        """Use cache if available, else run LLM scoring and cache the result."""
        jd_text = jd_text.strip()
        resume_text = resume_text.strip()

        cache = CacheHandler()
        cached_result = cache.get_cached_result(jd_text, resume_text)

        if cached_result:
            return cached_result

        embedding_model = LLMHandler.get_embedding_model()
        doc = Document(page_content=resume_text, metadata={"source": "resume"})
        qa_chain = LLMHandler.create_qa_chain([doc], embedding_model)

        if not qa_chain:
            return "No relevant content found in resume."

        result = qa_chain.run(jd_text)
        cache.store_result(jd_text, resume_text, result)
        return result