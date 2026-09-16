import faiss
import numpy as np
import json
import os

VECTORSTORE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vectorstore")

class VectorStore:
    def __init__(self):
        self.index = None
        self.chunks = []
        self.sources = []
        self.dimension = 384
    
    def construire(self, chunks, sources, embeddings):
        self.chunks = chunks
        self.sources = sources
        
        self.index = faiss.IndexFlatIP(self.dimension)
        
        normes = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_normalises = embeddings / normes
        self.index.add(embeddings_normalises.astype(np.float32))
        
        os.makedirs(VECTORSTORE_DIR, exist_ok=True)
        faiss.write_index(self.index, os.path.join(VECTORSTORE_DIR, "index.faiss"))
        
        with open(os.path.join(VECTORSTORE_DIR, "chunks.json"), "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False)
        
        with open(os.path.join(VECTORSTORE_DIR, "sources.json"), "w", encoding="utf-8") as f:
            json.dump(self.sources, f, ensure_ascii=False)
        
        print(f"Index construit: {len(chunks)} chunks, {self.index.ntotal} vecteurs")
        return True
    
    def charger(self):
        index_path = os.path.join(VECTORSTORE_DIR, "index.faiss")
        chunks_path = os.path.join(VECTORSTORE_DIR, "chunks.json")
        sources_path = os.path.join(VECTORSTORE_DIR, "sources.json")
        
        if not os.path.exists(index_path):
            return False
        
        self.index = faiss.read_index(index_path)
        
        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
        
        with open(sources_path, "r", encoding="utf-8") as f:
            self.sources = json.load(f)
        
        print(f"Index charge: {self.index.ntotal} vecteurs")
        return True
    
    def rechercher(self, query_embedding, k=5):
        if self.index is None:
            return []
        
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        norme = np.linalg.norm(query_embedding, axis=1, keepdims=True)
        query_normalise = query_embedding / norme
        
        scores, indices = self.index.search(query_normalise.astype(np.float32), k)
        
        resultats = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                resultats.append({
                    "texte": self.chunks[idx],
                    "score": float(score),
                    "source": self.sources[idx]
                })
        
        return resultats
    
    def existe(self):
        return os.path.exists(os.path.join(VECTORSTORE_DIR, "index.faiss"))
