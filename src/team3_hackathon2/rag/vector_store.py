import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings
from langchain_postgres import PGVector


PROJECT_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(
    PROJECT_ROOT / ".env"
)


CONNECTION_STRING = os.getenv(
    "PGVECTOR_CONNECTION_STRING",
    "postgresql+psycopg://langchain:langchain@localhost:5445/vectorstore",
)

COLLECTION_NAME = os.getenv(
    "PGVECTOR_COLLECTION_NAME",
    "vendor_assessment",
)


def get_embeddings() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv(
            "AZURE_EMBEDDING_ENDPOINT"
        ),
        api_key=os.getenv(
            "AZURE_EMBEDDING_API_KEY"
        ),
        azure_deployment=os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        ),
        api_version=os.getenv(
            "AZURE_OPENAI_API_VERSION"
        ),
    )


def get_vector_store() -> PGVector:
    return PGVector(
        embeddings=get_embeddings(),
        connection=CONNECTION_STRING,
        collection_name=COLLECTION_NAME,
        use_jsonb=True,
    )