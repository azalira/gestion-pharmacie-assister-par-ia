from .embeddings import encoder_single
from .vectorstore import VectorStore

_store = None

def get_store():
    global _store
    if _store is None:
        _store = VectorStore()
        if not _store.charger():
            print("Index non trouve. Lancez 'python build_index.py' pour le construire.")
    return _store

def rechercher(question, k=5, score_min=0.2):
    store = get_store()
    if store.index is None:
        return []
    
    query_emb = encoder_single(question)
    resultats = store.rechercher(query_emb, k=k)
    
    resultats_filtres = [r for r in resultats if r["score"] >= score_min]
    
    return resultats_filtres

def construire_index(chunks, sources, embeddings):
    store = VectorStore()
    store.construire(chunks, sources, embeddings)
    return store
