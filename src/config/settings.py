"""Application settings and configuration"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment and config file"""
    
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    gemini_api_key: Optional[str] = Field(None, env="GEMINI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    postgres_host: str = Field("localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    postgres_user: str = Field("postgres", env="POSTGRES_USER")
    postgres_password: str = Field("postgres", env="POSTGRES_PASSWORD")
    postgres_db: str = Field("sample_db", env="POSTGRES_DB")
    
    mysql_host: str = Field("localhost", env="MYSQL_HOST")
    mysql_port: int = Field(3306, env="MYSQL_PORT")
    mysql_user: str = Field("root", env="MYSQL_USER")
    mysql_password: str = Field("mysql", env="MYSQL_PASSWORD")
    mysql_db: str = Field("sample_db", env="MYSQL_DB")
    
    neo4j_uri: str = Field("bolt://localhost:7687", env="NEO4J_URI")
    neo4j_user: str = Field("neo4j", env="NEO4J_USER")
    neo4j_password: str = Field("neo4jpassword", env="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", env="NEO4J_DATABASE")
    
    neptune_endpoint: Optional[str] = Field(None, env="NEPTUNE_ENDPOINT")
    neptune_port: int = Field(8182, env="NEPTUNE_PORT")
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_reload: bool = Field(True, env="API_RELOAD")
    
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    embedding_provider: str = Field("openai", env="EMBEDDING_PROVIDER")  # openai or gemini
    embedding_model: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(1536, env="EMBEDDING_DIMENSION")

    openai_embedding_model: str = Field("text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    gemini_embedding_model: str = Field("models/text-embedding-004", env="GEMINI_EMBEDDING_MODEL")
    
    llm_provider: str = Field("openai", env="LLM_PROVIDER")  # openai, gemini, or anthropic
    llm_model: str = Field("gpt-4-turbo-preview", env="LLM_MODEL")
    llm_temperature: float = Field(0.0, env="LLM_TEMPERATURE")
    max_tokens: int = Field(4096, env="MAX_TOKENS")

    schema_llm_enabled: bool = Field(True, env="SCHEMA_LLM_ENABLED")
    schema_llm_provider: str = Field("openai", env="SCHEMA_LLM_PROVIDER")  # openai or gemini
    schema_llm_model: str = Field("gpt-4o-mini", env="SCHEMA_LLM_MODEL")

    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")
    gemini_model: str = Field("gemini-1.5-flash", env="GEMINI_MODEL")

    vector_store_path: str = Field("data/vector_store", env="VECTOR_STORE_PATH")

    cdc_enabled: bool = Field(False, env="CDC_ENABLED")
    cdc_mode: str = Field("native", env="CDC_MODE")  # native, polling, hybrid
    cdc_batch_size: int = Field(100, env="CDC_BATCH_SIZE")
    cdc_batch_timeout: float = Field(5.0, env="CDC_BATCH_TIMEOUT")
    cdc_enable_batching: bool = Field(True, env="CDC_ENABLE_BATCHING")
    cdc_sync_embeddings: bool = Field(True, env="CDC_SYNC_EMBEDDINGS")

    postgres_cdc_slot_name: str = Field("graph_sync_slot", env="POSTGRES_CDC_SLOT_NAME")
    postgres_cdc_publication: str = Field("graph_sync_pub", env="POSTGRES_CDC_PUBLICATION")
    postgres_cdc_tables: Optional[str] = Field(None, env="POSTGRES_CDC_TABLES")  # Comma-separated

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env
    
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def mysql_url(self) -> str:
        """Get MySQL connection URL"""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def load_yaml_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load YAML configuration file"""
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    return {}

