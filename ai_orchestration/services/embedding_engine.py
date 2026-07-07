import os
import faiss
import numpy as np
import logging
import json
from typing import List, Dict, Optional
from ai_orchestration.core.config import PROJECT_ROOT

logger = logging.getLogger("SnLag_EmbeddingEngine")

class EmbeddingEngine:
    """
    Requirement 4: AI Embedding Engine (FAISS Integration)
    Requirement 7: Deletion of embeddings on rollback
    Handles high-dimensional vector storage and semantic retrieval for sign language data.
    """
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.store_dir = os.path.join(PROJECT_ROOT, "vector_store")
        self.index_path = os.path.join(self.store_dir, "sign_embeddings.index")
        self.map_path = os.path.join(self.store_dir, "id_map.json")

        os.makedirs(self.store_dir, exist_ok=True)

        # We use IndexIDMap to allow deletion of specific vectors by ID
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                logger.info(f"EmbeddingEngine: Loaded existing index with {self.index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"EmbeddingEngine: Failed to load index: {e}")
                self.index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
        else:
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
            logger.info("EmbeddingEngine: Initialized new FAISS IndexIDMap.")

        if os.path.exists(self.map_path):
            with open(self.map_path, 'r') as f:
                self.id_map = json.load(f) # UUID -> Int ID
        else:
            self.id_map = {}

    def _get_next_id(self):
        return len(self.id_map)

    def add_embedding(self, vector: List[float], dataset_id: str, label: str):
        """Adds a vector with a specific ID mapping for later retrieval or deletion."""
        try:
            v_array = np.array([vector]).astype('float32')
            if v_array.shape[1] != self.dimension:
                new_v = np.zeros((1, self.dimension), dtype='float32')
                dim_min = min(v_array.shape[1], self.dimension)
                new_v[0, :dim_min] = v_array[0, :dim_min]
                v_array = new_v

            int_id = self.id_map.get(dataset_id)
            if int_id is None:
                int_id = self._get_next_id()
                self.id_map[dataset_id] = int_id

            ids = np.array([int_id]).astype('int64')
            self.index.add_with_ids(v_array, ids)

            self.save()
            return True
        except Exception as e:
            logger.error(f"EmbeddingEngine: Failed to add embedding: {e}")
            return False

    def remove_embedding(self, dataset_id: str):
        """Requirement 7: Remove embeddings on dataset rollback."""
        try:
            int_id = self.id_map.get(dataset_id)
            if int_id is not None:
                ids_to_remove = np.array([int_id]).astype('int64')
                self.index.remove_ids(ids_to_remove)
                del self.id_map[dataset_id]
                self.save()
                logger.info(f"EmbeddingEngine: Removed embedding for DS#{dataset_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"EmbeddingEngine: Failed to remove embedding: {e}")
            return False

    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.map_path, 'w') as f:
            json.dump(self.id_map, f)

    def search(self, vector: List[float], k: int = 5):
        try:
            v_array = np.array([vector]).astype('float32')
            distances, indices = self.index.search(v_array, k)
            # Map back to UUIDs
            reverse_map = {v: k for k, v in self.id_map.items()}
            results = []
            for d, i in zip(distances[0], indices[0]):
                if i != -1:
                    results.append({"dataset_id": reverse_map.get(i), "distance": float(d)})
            return results
        except Exception as e:
            logger.error(f"EmbeddingEngine: Search failed: {e}")
            return []

# Singleton Instance
embedding_engine = EmbeddingEngine()
