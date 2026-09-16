#!/usr/bin/env python3
"""
Evaluation du chatbot pharmacie fine-tune.

Calcule des metriques sur le jeu de validation :
  - Exact Match (EM) : la reponse predite est exactement egale a la reponse attendue
  - Token Overlap (F1) : chevauchement de tokens (style SQuAD)
  - Containment : la reponse attendue est contenue dans la reponse predite
  - Latence moyenne

Usage :
  python ml/src/evaluate.py --model ml/models/pharma_bot_v1
  python ml/src/evaluate.py --model ml/models/pharma_bot_v1 --limit 20
"""

import argparse
import json
import re
import string
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ML_DATA = ROOT / "ml" / "data"


def normalize_answer(s):
    """Normalise une reponse pour comparaison (lowercase, ponctuation, espaces)."""
    def remove_articles(text):
        return re.sub(r"\b(a|an|the|le|la|les|un|une|des|du|de)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def f1_score(prediction, ground_truth):
    """Calcule le F1 token (style SQuAD)."""
    pred_tokens = normalize_answer(prediction).split()
    gt_tokens = normalize_answer(ground_truth).split()

    if len(pred_tokens) == 0 or len(gt_tokens) == 0:
        return int(pred_tokens == gt_tokens)

    common = set(pred_tokens) & set(gt_tokens)
    if not common:
        return 0

    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(gt_tokens)
    return 2 * (precision * recall) / (precision + recall)


def exact_match(prediction, ground_truth):
    return int(normalize_answer(prediction) == normalize_answer(ground_truth))


def contains(prediction, ground_truth):
    return int(normalize_answer(ground_truth) in normalize_answer(prediction))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, help="Limiter le nombre d'exemples valides")
    parser.add_argument("--output", help="Fichier JSON de sortie (resultats detailles)")
    args = parser.parse_args()

    val_path = ML_DATA / "val.json"
    if not val_path.exists():
        print(f"Erreur : {val_path} introuvable.")
        print("Lancer : python ml/src/preprocessing.py")
        return

    val_data = json.loads(val_path.read_text(encoding="utf-8"))
    if args.limit:
        val_data = val_data[:args.limit]

    print(f"Evaluation sur {len(val_data)} exemples...")

    sys.path.insert(0, str(Path(__file__).parent))
    from predict import load_model, generate, check_dependencies

    check_dependencies()
    model, tokenizer, device = load_model(args.model)

    results = []
    em_scores = []
    f1_scores = []
    containment_scores = []
    latencies = []

    for i, example in enumerate(val_data, 1):
        messages = example["messages"]
        question = next(m["content"] for m in messages if m["role"] == "user")
        expected = next(m["content"] for m in messages if m["role"] == "assistant")

        t0 = time.time()
        prediction = generate(model, tokenizer, device, question, max_new_tokens=200)
        latency = time.time() - t0
        latencies.append(latency)

        em = exact_match(prediction, expected)
        f1 = f1_score(prediction, expected)
        cont = contains(prediction, expected)

        em_scores.append(em)
        f1_scores.append(f1)
        containment_scores.append(cont)

        results.append({
            "question": question,
            "expected": expected,
            "prediction": prediction,
            "em": em,
            "f1": round(f1, 3),
            "containment": cont,
            "latency_s": round(latency, 2),
        })

        if i % 5 == 0 or i == len(val_data):
            print(f"  [{i}/{len(val_data)}] "
                  f"EM={sum(em_scores)/i:.2%} "
                  f"F1={sum(f1_scores)/i:.2%} "
                  f"Contain={sum(containment_scores)/i:.2%} "
                  f"Lat={sum(latencies)/i:.1f}s")

    summary = {
        "n_examples": len(val_data),
        "exact_match": sum(em_scores) / len(em_scores),
        "f1_score": sum(f1_scores) / len(f1_scores),
        "containment": sum(containment_scores) / len(containment_scores),
        "avg_latency_s": sum(latencies) / len(latencies),
        "p95_latency_s": sorted(latencies)[int(0.95 * len(latencies))],
    }

    print("\n" + "=" * 50)
    print(" Resultats finaux")
    print("=" * 50)
    print(f"  Exact Match     : {summary['exact_match']:.2%}")
    print(f"  F1 Score        : {summary['f1_score']:.2%}")
    print(f"  Containment     : {summary['containment']:.2%}")
    print(f"  Latence moyenne : {summary['avg_latency_s']:.1f}s")
    print(f"  Latence P95     : {summary['p95_latency_s']:.1f}s")

    if args.output:
        Path(args.output).write_text(
            json.dumps({"summary": summary, "details": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nResultats detailles dans {args.output}")


if __name__ == "__main__":
    import sys
    main()
