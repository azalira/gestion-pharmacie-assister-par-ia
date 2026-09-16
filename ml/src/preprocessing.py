#!/usr/bin/env python3
"""
Generation du dataset d'entrainement pour le chatbot pharmacie.

Sources :
  - symptomes_db.py     -> Q/A medicament <-> symptomes
  - knowledge_base.py   -> Q/A gestion de stock
  - BDPM (specialites)  -> Q/A informations medicaments
  - OpenFDA (anti-emetiques) -> enrichissement

Format de sortie : JSONL compatible avec instruction-tuning (chatml / llama).

Exemple de ligne :
  {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

Modeles compatibles : TinyLlama, Phi-2, Mistral (via TRL / HuggingFace trainer).
"""

import json
import os
import random
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_IA = ROOT / "backend" / "app" / "ia"
ML_DATA = ROOT / "ml" / "data"
ML_DATA.mkdir(parents=True, exist_ok=True)

random.seed(42)

INTRO = (
    "Tu es un assistant pharmacien francophone. Tu donnes des informations sur les "
    "medicaments, leurs indications, leurs symptomes et la gestion de stock en pharmacie. "
    "Tu n'es pas un medecin. Consulte toujours un professionnel de sante."
)

FRANCAIS_EXAMPLES = {
    "vomissement": ["vomissements", "vomir", "envie de vomir", "nausees et vomissements"],
    "fievre": ["temperature elevee", "fievre et frissons", "hyperthermie"],
    "douleur": ["mal a", "douleur au", "ca fait mal"],
    "diarrhee": ["selles liquides", "diarrhee aigue"],
    "toux": ["tousser", "toux seche", "toux grasse"],
    "infection": ["infection bacterienne", "signe d'infection"],
}


def load_symptomes():
    sys.path.insert(0, str(BACKEND_IA))
    from symptomes_db import SYMPTOMES_MEDIAMENTS
    return SYMPTOMES_MEDIAMENTS


def load_knowledge():
    sys.path.insert(0, str(BACKEND_IA))
    from knowledge_base import KNOWLEDGE
    return KNOWLEDGE


def generate_medicament_qa(medocs):
    qa_pairs = []
    for nom, info in medocs.items():
        symptomes = info["symptomes"]
        classe = info["classe"]
        substances = info["substances"]

        qa_pairs.append({
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user",
                 "content": f"Quels sont les medicaments pour {symptomes[0]} ?"},
                {"role": "assistant",
                 "content": f"{nom} est un medicament de la classe {classe} "
                            f"({', '.join(substances)}). Il est indicated pour : "
                            f"{', '.join(symptomes)}."}
            ]
        })

        qa_pairs.append({
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user",
                 "content": f"Que traite le medicament {nom} ?"},
                {"role": "assistant",
                 "content": f"{nom} (substances : {', '.join(substances)}) "
                            f"appartient a la classe {classe}. "
                            f"Il est utilise pour : {', '.join(symptomes)}."}
            ]
        })

        qa_pairs.append({
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user",
                 "content": f"J'ai des {symptomes[0]}. Quel medicament recommandez-vous ?"},
                {"role": "assistant",
                 "content": f"Pour des {symptomes[0]}, {nom} pourrait etre indique "
                            f"(classe therapeutique : {classe}). Les symptomes traites : "
                            f"{', '.join(symptomes)}."}
            ]
        })

        if len(substances) == 1:
            qa_pairs.append({
                "messages": [
                    {"role": "system", "content": INTRO},
                    {"role": "user",
                     "content": f"Quel est le principe actif de {nom} ?"},
                    {"role": "assistant",
                     "content": f"Le principe actif de {nom} est {substances[0]}."}
                ]
            })

        qa_pairs.append({
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user",
                 "content": f"Quelle est la classe therapeutique de {nom} ?"},
                {"role": "assistant",
                 "content": f"{nom} appartient a la classe {classe}."}
            ]
        })

        for i, s1 in enumerate(symptomes):
            for s2 in symptomes[i + 1:]:
                qa_pairs.append({
                    "messages": [
                        {"role": "system", "content": INTRO},
                        {"role": "user",
                         "content": f"Quels medicaments contre {s1} et {s2} ?"},
                        {"role": "assistant",
                         "content": f"{nom} est indicated pour {s1} et {s2} "
                                    f"(classe : {classe})."}
                    ]
                })

        enrichis = FRANCAIS_EXAMPLES.get(symptomes[0], [])
        for variant in enrichis:
            qa_pairs.append({
                "messages": [
                    {"role": "system", "content": INTRO},
                    {"role": "user",
                     "content": f"J'ai des {variant}. Que prendre ?"},
                    {"role": "assistant",
                     "content": f"Pour des {variant}, {nom} peut etre indicated "
                                f"({classe}, substances : {', '.join(substances)})."}
                ]
            })

    return qa_pairs


def generate_stock_qa(knowledge):
    qa_pairs = []
    for key, entry in knowledge.items():
        q = entry["question"]
        r = entry["reponse"]
        qa_pairs.append({
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user", "content": q},
                {"role": "assistant", "content": r}
            ]
        })

        qa_pairs.append({
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user", "content": q.lower()},
                {"role": "assistant", "content": r}
            ]
        })

        generiques = [
            q.lower().replace("cmm", "consommation moyenne mensuelle"),
            q.lower().replace("ss", "stock de securite"),
            q.lower().replace("smin", "stock minimum"),
            q.lower().replace("smax", "stock maximum"),
            q.lower().replace("qac", "quantite a commander"),
            q.lower().replace("sr", "stock de roulement"),
        ]
        for gq in generiques:
            if gq != q.lower():
                qa_pairs.append({
                    "messages": [
                        {"role": "system", "content": INTRO},
                        {"role": "user", "content": gq},
                        {"role": "assistant", "content": r}
                    ]
                })

    return qa_pairs


def generate_consultation_qa(medocs):
    qa_pairs = []
    questions_consultation = [
        ("J'ai mal a la tete et de la fievre, que prendre ?",
         "Pour la douleur et la fievre, les antalgiques comme le Paracetamol "
         "ou l'Ibuprofene sont souvent recommandes. Consultez un pharmacien pour le bon choix."),
        ("Mon enfant a de la diarrhee, quel medicament ?",
         "Smecta (Diosmectite) est souvent utilise pour la diarrhee. "
         "Consultez un medecin si les symptomes persistent ou s'aggravent."),
        ("J'ai des brulures d'estomac, que me conseillez-vous ?",
         "Pour les brulures d'estomac, Gaviscon ou Mugrucaine (alginate) "
         "sont souvent recommandes.Consultez un medecin si les symptomes persistent."),
        ("J'ai une toux seche, quel traitement ?",
         "Pour la toux seche, un antitussif comme le Doliprane Codeine peut etre indicated. "
         "Buvez beaucoup et hydratez-vous."),
        ("J'ai le nez bouche, que faire ?",
         "Pour le nez bouche, Sterimar (lavage nasal a l'eau de mer) ou "
         "Sinupret (fluidifiant nasal) peuvent aider."),
        ("Je suis allergique, quel antihistaminique ?",
         "Zyrtec (Cetirizine) ou Clarityn (Loratadine) sont des antihistaminiques courants. "
         "Consultez un medecin pour identifier l'allergene."),
        ("J'ai mal a la gorge, que prendre ?",
         "Pour le mal de gorge, Paracetamol ou Ibuprofene peuvent soulager. "
         "Consultez un medecin si la douleur persiste plus de quelques jours."),
        ("Je suis enerve/stressee, que me conseillez-vous ?",
         "Pour l'anxiete et le stress, Seresta (Oxazepam) est parfois prescribed. "
         "Des techniques de relaxation peuvent aussi aider. Consultez un medecin."),
        ("J'ai des hemorroides, que prendre ?",
         " Daflon (Diosmine + Hesperidine) est souvent utilise pour les hemorroides. "
         "Consultez un medecin si les symptomes persistent."),
        ("J'ai des regles douloureuses, que prendre ?",
         "Pour les regles douloureuses, Ibuprofene ou Spasfon sont souvent recommandes. "
         "Consultez un medecin ou pharmacien."),
        ("J'ai des douleurs articulaires, que faire ?",
         "Pour les douleurs articulaires, Ibuprofene ou Paracetamol peuvent aider. "
         "Consultez un medecin si les douleurs persistent."),
        ("Je tousse depuis 3 jours, est-ce grave ?",
         "Une toux persistante (plus de quelques jours) justifie une consultation medicale. "
         "En attendant, hydratez-vous bien et utilisez un antitussif si la toux est seche."),
        ("J'ai pris trop de medicaments, que faire ?",
         "Appelez immediatement le 15 (SAMU) ou le centre antipoison. Ne provoquez pas "
         "de vomissement sans avis medical."),
    ]

    for q, r in questions_consultation:
        qa_pairs.append({
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user", "content": q},
                {"role": "assistant", "content": r}
            ]
        })

    return qa_pairs


def generate_conversation_qa(medocs):
    conversations = [
        {
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user", "content": "Bonjour, j'ai des nausees"},
                {"role": "assistant",
                 "content": "Bonjour ! Pour les nausees, Mugrucaine est souvent indicated. "
                            "Pouvez-vous me dire si vous avez aussi des brulures d'estomac ou des vomissements ?"},
                {"role": "user", "content": "Oui, j'ai aussi des vomissements"},
                {"role": "assistant",
                 "content": "Les vomissements avec nausees peuvent indiquer une gastro-enterite. "
                            "Mugrucaine ou un antiemetique comme le Metoclopramide peuvent aider. "
                            "Consultez un medecin si les symptomes persistent plus de 24h."},
                {"role": "user", "content": "Merci beaucoup !"},
                {"role": "assistant",
                 "content": "De rien ! N'hesitez pas a consulter un pharmacien ou un medecin "
                            "pour un avis personnalise. Prenez soin de vous !"}
            ]
        },
        {
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user", "content": "Quel est le stock de Paracetamol ?"},
                {"role": "assistant",
                 "content": "Je n'ai pas acces au stock en temps reel dans cette conversation. "
                            "Utilisez l'interface Dashboard pour consulter les niveaux de stock."},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": INTRO},
                {"role": "user", "content": "Comment calculer le stock de securite ?"},
                {"role": "assistant",
                 "content": "Le Stock de Securite (SS) se calcule ainsi : "
                            "SS = 0.5 x CMM x (delai de livraison / 30). "
                            "Il represente la moitie de la consommation entre deux commandes."},
            ]
        },
    ]
    return conversations


def to_chatml(example):
    lines = []
    for msg in example["messages"]:
        role = msg["role"]
        if role == "system":
            lines.append(f"<|im_start|>system\n{msg['content']}<|im_end|>")
        elif role == "user":
            lines.append(f"<|im_start|>user\n{msg['content']}<|im_end|>")
        elif role == "assistant":
            lines.append(f"<|im_start|>assistant\n{msg['content']}<|im_end|>")
    lines.append("<|im_end|>")
    return "\n".join(lines)


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generation du dataset...")

    medocs = load_symptomes()
    print(f"  Symptomes DB : {len(medocs)} medicaments")

    knowledge = load_knowledge()
    print(f"  Knowledge base : {len(knowledge)} entrees")

    all_qa = []
    all_qa.extend(generate_medicament_qa(medocs))
    print(f"  Q/A medicaments : {len(all_qa)}")

    stock_qa = generate_stock_qa(knowledge)
    all_qa.extend(stock_qa)
    print(f"  Q/A stock : {len(stock_qa)}")

    consult_qa = generate_consultation_qa(medocs)
    all_qa.extend(consult_qa)
    print(f"  Q/A consultation : {len(consult_qa)}")

    conv_qa = generate_conversation_qa(medocs)
    all_qa.extend(conv_qa)
    print(f"  Q/A conversation : {len(conv_qa)}")

    random.shuffle(all_qa)
    total = len(all_qa)
    print(f"  Total : {total} exemples (melanges)")

    split_train = int(total * 0.9)
    train_data = all_qa[:split_train]
    val_data = all_qa[split_train:]

    train_json = ML_DATA / "train.json"
    val_json = ML_DATA / "val.json"
    train_chatml = ML_DATA / "train_chatml.jsonl"
    val_chatml = ML_DATA / "val_chatml.jsonl"

    train_json.write_text(json.dumps(train_data, ensure_ascii=False, indent=2), encoding="utf-8")
    val_json.write_text(json.dumps(val_data, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(train_chatml, "w", encoding="utf-8") as f:
        for ex in train_data:
            f.write(to_chatml(ex) + "\n")

    with open(val_chatml, "w", encoding="utf-8") as f:
        for ex in val_data:
            f.write(to_chatml(ex) + "\n")

    print(f"  train.json       : {train_json} ({len(train_data)} examples)")
    print(f"  val.json         : {val_json} ({len(val_data)} examples)")
    print(f"  train_chatml.jsonl : format chatml (pour TRL trainer)")
    print(f"  val_chatml.jsonl   : format chatml")
    print(f"\nDataset pret pour l'entrainement !")
    print(f"  -> Lancer : python ml/src/train.py")


if __name__ == "__main__":
    main()
