"""Embedding service for generating vector embeddings"""

from typing import List, Union, Optional
import numpy as np
from openai import OpenAI
import google.generativeai as genai
from loguru import logger


class EmbeddingService:
    """Service for generating embeddings using OpenAI or Google Gemini"""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        provider: str = "openai"
    ):
        """
        Initialize embedding service

        Args:
            api_key: API key for the provider
            model: Embedding model to use
            provider: Provider to use ('openai' or 'gemini')
        """
        self.provider = provider.lower()
        self.model = model

        if self.provider == "openai":
            self.client = OpenAI(api_key=api_key)
            self.dimension = 1536 if "small" in model else 3072
        elif self.provider == "gemini":
            genai.configure(api_key=api_key)
            self.dimension = 768
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            if self.provider == "openai":
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                return response.data[0].embedding
            elif self.provider == "gemini":
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                return result['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding with {self.provider}: {e}")
            raise
    
    def embed_texts(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch

        Returns:
            List of embedding vectors
        """
        embeddings = []

        if self.provider == "openai":
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                try:
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.model
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    embeddings.extend(batch_embeddings)
                except Exception as e:
                    logger.error(f"Error generating batch embeddings: {e}")
                    raise
        elif self.provider == "gemini":
            for text in texts:
                try:
                    result = genai.embed_content(
                        model=self.model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                except Exception as e:
                    logger.error(f"Error generating embedding for text: {e}")
                    raise

        return embeddings
    
    def embed_node(self, node_data: dict) -> List[float]:
        """
        Generate embedding for a graph node
        
        Args:
            node_data: Node properties dictionary
            
        Returns:
            Embedding vector
        """
        text_parts = []
        
        if "label" in node_data:
            text_parts.append(f"Type: {node_data['label']}")
        
        for key, value in node_data.items():
            if key != "label" and value is not None:
                text_parts.append(f"{key}: {value}")
        
        text = " | ".join(text_parts)
        return self.embed_text(text)
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return dot_product / (norm_v1 * norm_v2)

