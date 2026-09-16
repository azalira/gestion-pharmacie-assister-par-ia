import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import bdpm_loader
import symptomes_db
from knowledge_base import KNOWLEDGE

def chunker_bdpm_light():
    chunks = []
    sources = []
    
    specialites = bdpm_loader.load_specialites()
    for s in specialites:
        text = f"Specialite: {s['nom']}. Forme: {s['forme']}. Voie: {s['voie']}. Statut: {s['commercialise']}. Titulaire: {s['titulaire']}."
        chunks.append(text)
        sources.append({"type": "bdpm", "cis": s['cis'], "nom": s['nom']})
    
    return chunks, sources

def chunker_knowledge():
    chunks = []
    sources = []
    
    for cle, entry in KNOWLEDGE.items():
        text = f"Question: {entry['question']}\nReponse: {entry['reponse']}"
        chunks.append(text)
        sources.append({"type": "knowledge", "cle": cle})
    
    return chunks, sources

def chunker_symptomes():
    chunks = []
    sources = []
    
    for nom, info in symptomes_db.SYMPTOMES_MEDIAMENTS.items():
        text = f"Medicament: {nom}. Classe: {info['classe']}. Substances: {', '.join(info['substances'])}. Utilise pour: {', '.join(info['symptomes'])}."
        chunks.append(text)
        sources.append({"type": "symptome", "nom": nom})
    
    return chunks, sources

def tout_chunker_light():
    chunks_knowledge, sources_knowledge = chunker_knowledge()
    chunks_symptomes, sources_symptomes = chunker_symptomes()
    
    all_chunks = chunks_knowledge + chunks_symptomes
    all_sources = sources_knowledge + sources_symptomes
    
    return all_chunks, all_sources
