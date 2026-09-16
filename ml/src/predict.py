#!/usr/bin/env python3
"""
Inference pour le chatbot pharmacie fine-tune.

Charge le modele LoRA entraine et genere des reponses a partir du chat.

Usage :
  # Mode interactif
  python ml/src/predict.py --model ml/models/pharma_bot_v1

  # Question unique
  python ml/src/predict.py --model ml/models/pharma_bot_v1 --question "J'ai mal a la tete"

  # Mode batch (depuis fichier)
  python ml/src/predict.py --model ml/models/pharma_bot_v1 --input questions.txt --output reponses.txt

Le script fusionne automatiquement les poids LoRA dans le modele de base
pour des performances optimales en inference.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


INTRO = (
    "Tu es un assistant pharmacien francophone. Tu donnes des informations sur les "
    "medicaments, leurs indications, leurs symptomes et la gestion de stock en pharmacie. "
    "Tu n'es pas un medecin. Consulte toujours un professionnel de sante."
)


def check_dependencies():
    missing = []
    try:
        import torch
    except ImportError:
        missing.append("torch")
    try:
        import transformers
    except ImportError:
        missing.append("transformers")
    try:
        import peft
    except ImportError:
        missing.append("peft")
    if missing:
        print("Dependances manquantes :", ", ".join(missing))
        print("Installer : pip install torch transformers peft accelerate")
        sys.exit(1)


def load_model(model_path, base_model=None):
    """Charge le modele fine-tune (LoRA merge)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    model_path = Path(model_path)

    info_file = model_path / "training_info.json"
    if info_file.exists() and base_model is None:
        info = json.loads(info_file.read_text())
        base_model = info.get("base_model", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    print(f"Chargement tokenizer : {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Chargement modele de base : {base_model}")
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float32,
        trust_remote_code=True,
    )

    print(f"Chargement des poids LoRA depuis {model_path}")
    model = PeftModel.from_pretrained(base, str(model_path))
    print("Fusion des poids LoRA...")
    model = model.merge_and_unload()

    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"Modele charge sur {device}")
    return model, tokenizer, device


def format_prompt(question, history=None):
    """Formate la conversation en prompt chatml."""
    messages = [{"role": "system", "content": INTRO}]
    if history:
        for h in history:
            messages.append({"role": "user", "content": h[0]})
            messages.append({"role": "assistant", "content": h[1]})
    messages.append({"role": "user", "content": question})

    prompt = ""
    for m in messages:
        prompt += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    return prompt


def generate(model, tokenizer, device, question, history=None,
             max_new_tokens=256, temperature=0.7, top_p=0.9):
    """Genere une reponse."""
    import torch

    prompt = format_prompt(question, history)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=(temperature > 0),
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return response.strip()


def interactive_mode(model, tokenizer, device):
    """Mode chat interactif."""
    print("=" * 60)
    print(" Chatbot Pharmacie - Mode interactif")
    print(" Tapez 'quit' pour quitter")
    print("=" * 60)

    history = []
    while True:
        try:
            q = input("\nVous: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir !")
            break
        if not q:
            continue
        if q.lower() in ("quit", "exit", "q", "quitter"):
            print("Au revoir !")
            break

        print("\nBot: ", end="", flush=True)
        r = generate(model, tokenizer, device, q, history)
        print(r)
        history.append((q, r))
        if len(history) > 4:
            history = history[-4:]


def single_question(model, tokenizer, device, question):
    """Genere une reponse a une question unique."""
    r = generate(model, tokenizer, device, question)
    print(f"Question : {question}")
    print(f"Reponse  : {r}")
    return r


def batch_mode(model, tokenizer, device, input_file, output_file):
    """Traite un fichier de questions (une par ligne)."""
    questions = Path(input_file).read_text(encoding="utf-8").strip().split("\n")
    responses = []
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q[:60]}...")
        r = generate(model, tokenizer, device, q)
        responses.append({"question": q, "reponse": r})

    Path(output_file).write_text(
        json.dumps(responses, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n{len(responses)} reponses sauvegardees dans {output_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Chemin du modele LoRA")
    parser.add_argument("--base-model", help="Modele de base (defaut: depuis training_info.json)")
    parser.add_argument("--question", "-q", help="Question unique")
    parser.add_argument("--input", "-i", help="Fichier de questions (une par ligne)")
    parser.add_argument("--output", "-o", help="Fichier de sortie (JSON)")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    if not Path(args.model).exists():
        print(f"Modele introuvable : {args.model}")
        print("Avez-vous lance l'entrainement ? python ml/src/train.py")
        sys.exit(1)

    check_dependencies()
    model, tokenizer, device = load_model(args.model, args.base_model)

    if args.question:
        single_question(model, tokenizer, device, args.question)
    elif args.input:
        if not args.output:
            print("--output requis avec --input")
            sys.exit(1)
        batch_mode(model, tokenizer, device, args.input, args.output)
    else:
        interactive_mode(model, tokenizer, device)


if __name__ == "__main__":
    main()
