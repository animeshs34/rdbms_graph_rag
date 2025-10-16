"""Vector store for similarity search"""

from typing import List, Dict, Any, Tuple
import numpy as np
import faiss
import pickle
from pathlib import Path
from loguru import logger


class VectorStore:
    """FAISS-based vector store for similarity search"""

    def __init__(self, dimension: int = 1536, storage_path: str = "data/vector_store", auto_save: bool = True):
        """
        Initialize vector store

        Args:
            dimension: Dimension of embedding vectors
            storage_path: Path to store/load the vector store
            auto_save: Whether to automatically save after adding vectors
        """
        self.dimension = dimension
        self.storage_path = Path(storage_path)
        self.auto_save = auto_save
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata: List[Dict[str, Any]] = []

        self._auto_load()
    
    def add_vectors(
        self,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> None:
        """
        Add vectors to the store

        Args:
            vectors: List of embedding vectors
            metadata: List of metadata dictionaries (one per vector)
        """
        if len(vectors) != len(metadata):
            raise ValueError("Number of vectors must match number of metadata items")

        vectors_np = np.array(vectors, dtype=np.float32)

        self.index.add(vectors_np)

        self.metadata.extend(metadata)

        logger.info(f"Added {len(vectors)} vectors to store. Total: {self.index.ntotal}")

        if self.auto_save:
            self._auto_save()
    
    def search(
        self, 
        query_vector: List[float], 
        top_k: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar vectors
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of (metadata, distance) tuples
        """
        query_np = np.array([query_vector], dtype=np.float32)
        
        distances, indices = self.index.search(query_np, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                results.append((self.metadata[idx], float(dist)))
        
        return results
    
    def save(self, path: str) -> None:
        """
        Save vector store to disk
        
        Args:
            path: Directory path to save to
        """
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        
        faiss.write_index(self.index, str(path_obj / "index.faiss"))
        
        with open(path_obj / "metadata.pkl", "wb") as f:
            pickle.dump(self.metadata, f)
        
        logger.info(f"Saved vector store to {path}")
    
    def load(self, path: str) -> None:
        """
        Load vector store from disk
        
        Args:
            path: Directory path to load from
        """
        path_obj = Path(path)
        
        self.index = faiss.read_index(str(path_obj / "index.faiss"))
        
        with open(path_obj / "metadata.pkl", "rb") as f:
            self.metadata = pickle.load(f)
        
        logger.info(f"Loaded vector store from {path}. Total vectors: {self.index.ntotal}")
    
    def clear(self) -> None:
        """Clear all vectors from the store"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        logger.info("Cleared vector store")

        if self.auto_save:
            self._auto_save()

    def _auto_load(self) -> None:
        """Automatically load vector store if it exists"""
        try:
            if (self.storage_path / "index.faiss").exists():
                self.load(str(self.storage_path))
                logger.info(f"Auto-loaded vector store with {self.size} vectors")
        except Exception as e:
            logger.warning(f"Could not auto-load vector store: {e}")

    def _auto_save(self) -> None:
        """Automatically save vector store"""
        try:
            self.save(str(self.storage_path))
        except Exception as e:
            logger.error(f"Failed to auto-save vector store: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get status information about the vector store"""
        return {
            "size": self.size,
            "dimension": self.dimension,
            "storage_path": str(self.storage_path),
            "auto_save": self.auto_save,
            "is_loaded": self.size > 0,
            "storage_exists": (self.storage_path / "index.faiss").exists()
        }

    @property
    def size(self) -> int:
        """Get number of vectors in store"""
        return self.index.ntotal

