import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector


PROJECT_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(
    PROJECT_ROOT / ".env"
)


CONNECTION_STRING = os.getenv(
    "PGVECTOR_CONNECTION_STRING",
    "postgresql+psycopg://langchain:langchain@localhost:5433/vectorstore",
)

COLLECTION_NAME = os.getenv(
    "PGVECTOR_COLLECTION_NAME",
    "vendor_assessment",
)


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )


def get_vector_store() -> PGVector:
    return PGVector(
        embeddings=get_embeddings(),
        connection=CONNECTION_STRING,
        collection_name=COLLECTION_NAME,
        use_jsonb=True,
    )
