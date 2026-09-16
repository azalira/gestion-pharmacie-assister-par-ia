from sentence_transformers import SentenceTransformer
import numpy as np

MODELE = "all-MiniLM-L6-v2"

_model = None

def get_model():
    global _model
    if _model is None:
        print(f"Chargement du modele {MODELE}...")
        _model = SentenceTransformer(MODELE)
        print("Modele charge !")
    return _model

def encoder(textes, batch_size=256):
    model = get_model()
    
    if isinstance(textes, str):
        textes = [textes]
    
    embeddings = model.encode(textes, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)
    return embeddings

def encoder_single(texte):
    model = get_model()
    embedding = model.encode([texte], convert_to_numpy=True)
    return embedding[0]
