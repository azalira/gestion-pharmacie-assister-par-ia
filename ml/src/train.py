#!/usr/bin/env python3
"""
Fine-tuning d'un petit LLM (TinyLlama-1.1B) pour le chatbot pharmacie.

Methodologie :
  - Modele de base : TinyLlama-1.1B-Chat-v1.0 (1.1B parametres, 1 Go RAM)
  - LoRA (Low-Rank Adaptation) : fine-tune efficace sans toucher au modele complet
  - Format : chatml (<|im_start|>user ... <|im_end|>assistant)
  - Loss : uniquement sur la reponse assistant (causal LM)

Usage :
  python ml/src/train.py --model TinyLlama/TinyLlama-1.1B-Chat-v1.0
  python ml/src/train.py --epochs 3 --batch-size 4

Notes :
  - Necessite : transformers, datasets, peft, accelerate, bitsandbytes (optionnel pour QLoRA)
  - CPU : fonctionne mais lent (~1-2h pour 3 epochs)
  - GPU : 10-20 min sur T4 (16 Go VRAM)
  - Si bitsandbytes indisponible, fallback LoRA classique (sans quantization)
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ML_DATA = ROOT / "ml" / "data"
ML_MODELS = ROOT / "ml" / "models"
ML_MODELS.mkdir(parents=True, exist_ok=True)


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
        import datasets
    except ImportError:
        missing.append("datasets")
    try:
        import peft
    except ImportError:
        missing.append("peft")
    try:
        import accelerate
    except ImportError:
        missing.append("accelerate")

    if missing:
        print("Dependances manquantes :")
        for m in missing:
            print(f"  - {m}")
        print("\nInstaller avec :")
        print("  pip install torch transformers datasets peft accelerate")
        if "bitsandbytes" in missing:
            print("  pip install bitsandbytes  # optionnel, pour QLoRA")
        sys.exit(1)


def load_dataset():
    """Charge train.json et val.json et prepare pour le trainer."""
    from datasets import Dataset

    train_path = ML_DATA / "train.json"
    val_path = ML_DATA / "val.json"

    if not train_path.exists():
        print(f"Erreur : {train_path} introuvable.")
        print("Lancer d'abord : python ml/src/preprocessing.py")
        sys.exit(1)

    train_data = json.loads(train_path.read_text(encoding="utf-8"))
    val_data = json.loads(val_path.read_text(encoding="utf-8"))

    def messages_to_text(example, tokenizer, max_length=512):
        """Convertit une conversation chatml en string tokenizable."""
        text = ""
        for msg in example["messages"]:
            if msg["role"] == "system":
                text += f"<|im_start|>system\n{msg['content']}<|im_end|>\n"
            elif msg["role"] == "user":
                text += f"<|im_start|>user\n{msg['content']}<|im_end|>\n"
            elif msg["role"] == "assistant":
                text += f"<|im_start|>assistant\n{msg['content']}<|im_end|>\n"
        text += "<|im_end|>"

        tokenized = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_tensors=None,
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    return Dataset.from_list(train_data), Dataset.from_list(val_data), messages_to_text


def train(args):
    check_dependencies()

    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training

    print(f"Modele : {args.model}")
    print(f"Epochs : {args.epochs}")
    print(f"Batch size : {args.batch_size}")
    print(f"Learning rate : {args.lr}")
    print(f"LoRA r={args.lora_r}, alpha={args.lora_alpha}")
    print(f"Quantization : {'4-bit (QLoRA)' if args.qlora else 'LoRA standard'}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device : {device}")
    if device == "cpu":
        print("  ATTENTION : CPU sera lent. Reduire --epochs a 1 pour test rapide.")

    print("\nChargement du tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Chargement du modele...")
    model_kwargs = {"trust_remote_code": True}

    if args.qlora and device == "cuda":
        try:
            from transformers import BitsAndBytesConfig
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            model_kwargs["quantization_config"] = bnb_config
            model_kwargs["torch_dtype"] = torch.float16
            print("  Quantization 4-bit activee (QLoRA)")
        except ImportError:
            print("  bitsandbytes non disponible, fallback LoRA standard")

    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)

    if args.qlora and device == "cuda":
        try:
            model = prepare_model_for_kbit_training(model)
        except Exception as e:
            print(f"  kbit prep echouee : {e}")

    print("Configuration LoRA...")
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("Chargement du dataset...")
    train_ds, val_ds, messages_to_text = load_dataset()

    def tokenize_fn(example):
        return messages_to_text(example, tokenizer, args.max_length)

    train_ds = train_ds.map(tokenize_fn, remove_columns=train_ds.column_names)
    val_ds = val_ds.map(tokenize_fn, remove_columns=val_ds.column_names)
    print(f"  Train : {len(train_ds)} exemples")
    print(f"  Val   : {len(val_ds)} exemples")

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    output_dir = ML_MODELS / args.output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        warmup_steps=50,
        weight_decay=0.01,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        report_to="none",
        fp16=(device == "cuda" and not args.qlora),
        bf16=False,
        gradient_accumulation_steps=args.gradient_accumulation,
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=data_collator,
    )

    print("\nDebut de l'entrainement...")
    trainer.train()

    print(f"\nSauvegarde du modele dans {output_dir}...")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    with open(output_dir / "training_info.json", "w") as f:
        json.dump({
            "base_model": args.model,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "lora_r": args.lora_r,
            "lora_alpha": args.lora_alpha,
            "qlora": args.qlora,
            "device": device,
            "train_size": len(train_ds),
            "val_size": len(val_ds),
        }, f, indent=2)

    print(f"\nEntrainement termine ! Modele sauvegarde dans : {output_dir}")
    print(f"Pour tester : python ml/src/predict.py --model {output_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                        help="Modele de base (HuggingFace)")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--qlora", action="store_true",
                        help="Activer QLoRA 4-bit (necessite bitsandbytes + GPU)")
    parser.add_argument("--output-name", default="pharma_bot_v1",
                        help="Nom du dossier de sortie")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
