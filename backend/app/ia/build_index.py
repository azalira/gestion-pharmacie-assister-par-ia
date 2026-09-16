import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from rag.chunker import tout_chunker_light, chunker_knowledge, chunker_symptomes
from rag.embeddings import encoder
from rag.retriever import construire_index
import argparse

def main():
    parser = argparse.ArgumentParser(description="Construire l'index RAG")
    parser.add_argument("--source", choices=["all", "knowledge", "symptomes"], default="all")
    args = parser.parse_args()
    
    print("=== Construction de l'index RAG ===\n")
    
    if args.source == "all":
        print("Chargement de toutes les sources...")
        chunks, sources = tout_chunker_light()
    elif args.source == "knowledge":
        print("Chargement de la base de connaissances...")
        chunks, sources = chunker_knowledge()
    elif args.source == "symptomes":
        print("Chargement des symptomes...")
        chunks, sources = chunker_symptomes()
    
    print(f"Total: {len(chunks)} chunks")
    
    print("\nGeneration des embeddings...")
    embeddings = encoder(chunks)
    print(f"Embeddings generes: {embeddings.shape}")
    
    print("\nConstruction de l'index FAISS...")
    construire_index(chunks, sources, embeddings)
    
    print("\n=== Index construit avec succes ! ===")

if __name__ == "__main__":
    main()
