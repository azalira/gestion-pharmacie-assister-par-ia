#!/usr/bin/env python3

"""
Génère un notebook Kaggle complet pour le fine-tuning
de TinyLlama 1.1B avec QLoRA.

Compatible avec :
- Kaggle
- GPU NVIDIA T4
- 1 ou 2 GPU T4
- Python 3.10+
- Transformers
- PEFT
- BitsAndBytes
- Datasets

Le notebook :
1. Vérifie le GPU
2. Installe les dépendances
3. Inspecte automatiquement /kaggle/input
4. Trouve les fichiers JSON du dataset
5. Charge le dataset
6. Détecte sa structure
7. Sépare train/validation si nécessaire
8. Charge TinyLlama
9. Configure QLoRA
10. Tokenise
11. Entraîne
12. Sauvegarde l'adapter LoRA
13. Crée un ZIP
"""

import json
import os
import ast


# ============================================================
# CONFIGURATION LOCALE
# ============================================================

# Racine du projet = parent du dossier scripts/ (fonctionne chez tout le monde)
PROJECT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

OUT = os.path.join(
    PROJECT,
    "ml",
    "notebooks",
    "kaggle_train.ipynb"
)


# ============================================================
# FONCTIONS
# ============================================================

def md(text):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            line + "\n"
            for line in text.strip("\n").split("\n")
        ],
    }


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            line + "\n"
            for line in text.strip("\n").split("\n")
        ],
    }


cells = []


# ============================================================
# CELLULE 1
# PRESENTATION
# ============================================================

cells.append(md("""
# 🤖 Fine-tuning TinyLlama 1.1B — Chatbot Pharmacie

Ce notebook permet d'entraîner TinyLlama avec **QLoRA 4-bit**
sur le dataset du projet de gestion de pharmacie.

## Configuration

- Modèle : `TinyLlama/TinyLlama-1.1B-Chat-v1.0`
- Méthode : QLoRA
- Quantification : 4-bit NF4
- LoRA : r=8
- LoRA alpha : 16
- GPU recommandé : NVIDIA T4
- Longueur maximale : 512 tokens

## Kaggle

Avant de lancer le notebook :

1. Activer **GPU**
2. Activer **Internet**
3. Ajouter le dataset `ia entre2`

Le notebook recherche automatiquement les fichiers JSON
dans `/kaggle/input/`.

## Sortie

Le modèle LoRA sera enregistré dans :

`/kaggle/working/pharma_bot_v1`

Puis un ZIP sera créé.
"""))


# ============================================================
# CELLULE 2
# GPU
# ============================================================

cells.append(code("""
#@title 1. Vérifier les GPU

import torch

print("=" * 60)
print("VERIFICATION DES GPU")
print("=" * 60)

if not torch.cuda.is_available():
    raise RuntimeError(
        "Aucun GPU CUDA détecté. "
        "Active GPU dans les paramètres Kaggle."
    )

gpu_count = torch.cuda.device_count()

print("Nombre de GPU :", gpu_count)
print()

for i in range(gpu_count):

    name = torch.cuda.get_device_name(i)

    props = torch.cuda.get_device_properties(i)

    vram = props.total_memory / (1024 ** 3)

    print(
        f"GPU {i} : {name} "
        f"| VRAM : {vram:.2f} Go"
    )

print()

torch.cuda.set_device(0)

torch.cuda.empty_cache()

print("GPU principal :", torch.cuda.get_device_name(0))
print("CUDA :", torch.version.cuda)
print("PyTorch :", torch.__version__)

print()
print("✅ GPU disponible.")
"""))


# ============================================================
# CELLULE 3
# DEPENDANCES
# ============================================================

cells.append(code("""
#@title 2. Installer les dépendances

!pip install -q -U \\
    "transformers>=4.45" \\
    datasets \\
    peft \\
    accelerate \\
    bitsandbytes \\
    sentencepiece
"""))


# ============================================================
# CELLULE 4
# INSPECTION DATASET
# ============================================================

cells.append(code("""
#@title 3. Inspecter les fichiers du dataset

import os
from pathlib import Path

INPUT_DIR = Path("/kaggle/input")

print("=" * 60)
print("CONTENU DE /kaggle/input")
print("=" * 60)

if not INPUT_DIR.exists():
    raise RuntimeError(
        "/kaggle/input n'existe pas."
    )

all_files = []

for path in INPUT_DIR.rglob("*"):

    if path.is_file():

        all_files.append(path)

        size_kb = path.stat().st_size / 1024

        print(
            f"{path} "
            f"({size_kb:.1f} Ko)"
        )

print()
print(
    f"Nombre de fichiers : {len(all_files)}"
)

if not all_files:

    raise RuntimeError(
        "Aucun fichier trouvé dans /kaggle/input. "
        "Ajoute le dataset avec '+ Add Input'."
    )

print()
print("✅ Dataset détecté.")
"""))


# ============================================================
# CELLULE 5
# CHARGEMENT AUTOMATIQUE JSON
# ============================================================

cells.append(code("""
#@title 4. Rechercher et charger le dataset JSON

import json
from pathlib import Path

json_files = list(
    Path("/kaggle/input").rglob("*.json")
)

print("=" * 60)
print("FICHIERS JSON")
print("=" * 60)

for path in json_files:

    size_kb = path.stat().st_size / 1024

    print(
        f"{path} "
        f"({size_kb:.1f} Ko)"
    )

if not json_files:

    raise FileNotFoundError(
        "Aucun fichier .json trouvé dans /kaggle/input."
    )


# ------------------------------------------------------------
# Chercher train / validation
# ------------------------------------------------------------

train_file = None
val_file = None

for path in json_files:

    name = path.name.lower()

    if name == "train.json":
        train_file = path

    elif name in [
        "val.json",
        "valid.json",
        "validation.json",
        "eval.json"
    ]:
        val_file = path


# ------------------------------------------------------------
# Si train/val existent
# ------------------------------------------------------------

if train_file is not None:

    print()
    print("Train trouvé :", train_file)

    with open(
        train_file,
        "r",
        encoding="utf-8"
    ) as f:

        train_raw = json.load(f)


    if val_file is not None:

        print(
            "Validation trouvée :",
            val_file
        )

        with open(
            val_file,
            "r",
            encoding="utf-8"
        ) as f:

            val_raw = json.load(f)

    else:

        val_raw = None


# ------------------------------------------------------------
# Sinon utiliser le premier JSON
# ------------------------------------------------------------

else:

    data_file = json_files[0]

    print()
    print(
        "Aucun train.json trouvé."
    )

    print(
        "Utilisation du fichier :",
        data_file
    )

    with open(
        data_file,
        "r",
        encoding="utf-8"
    ) as f:

        data_raw = json.load(f)


    # Cas liste
    if isinstance(data_raw, list):

        train_raw = data_raw

    # Cas dictionnaire
    elif isinstance(data_raw, dict):

        if "data" in data_raw:
            train_raw = data_raw["data"]

        elif "examples" in data_raw:
            train_raw = data_raw["examples"]

        elif "messages" in data_raw:
            train_raw = [data_raw["messages"]]

        else:

            train_raw = [
                data_raw
            ]

    else:

        raise ValueError(
            "Format JSON non supporté."
        )

    val_raw = None


print()
print("=" * 60)
print("DATASET CHARGE")
print("=" * 60)

print(
    "Train :",
    len(train_raw)
)

if val_raw is not None:

    print(
        "Validation :",
        len(val_raw)
    )

else:

    print(
        "Validation : aucune"
    )


print()
print("Premier exemple :")

print(
    json.dumps(
        train_raw[0],
        ensure_ascii=False,
        indent=2
    )
)
"""))


# ============================================================
# CELLULE 6
# PREPARATION TRAIN / VALIDATION
# ============================================================

cells.append(code("""
#@title 5. Préparer Train / Validation

from datasets import Dataset

print("=" * 60)
print("PREPARATION DES DATASETS")
print("=" * 60)


# ------------------------------------------------------------
# Vérifier le format
# ------------------------------------------------------------

if not isinstance(train_raw, list):

    raise ValueError(
        "Le dataset train doit être une liste."
    )


if len(train_raw) < 2:

    raise ValueError(
        "Le dataset contient moins de 2 exemples."
    )


# ------------------------------------------------------------
# Créer validation automatiquement si nécessaire
# ------------------------------------------------------------

if val_raw is None:

    print(
        "Aucune validation trouvée."
    )

    print(
        "Création automatique d'une validation de 10%."
    )

    split_index = int(
        len(train_raw) * 0.9
    )

    train_raw, val_raw = (
        train_raw[:split_index],
        train_raw[split_index:]
    )


# ------------------------------------------------------------
# Dataset Hugging Face
# ------------------------------------------------------------

train_dataset = Dataset.from_list(
    train_raw
)

val_dataset = Dataset.from_list(
    val_raw
)


print()
print(
    "Train :",
    len(train_dataset)
)

print(
    "Validation :",
    len(val_dataset)
)

print()
print("Colonnes :")
print(
    train_dataset.column_names
)


print()
print("✅ Dataset prêt.")
"""))


# ============================================================
# CELLULE 7
# CONFIGURATION
# ============================================================

cells.append(code("""
#@title 6. Configuration du fine-tuning

CONFIG = {

    "base_model":
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0",

    "epochs":
        5,

    "batch_size":
        4,

    "gradient_accumulation":
        2,

    "lr":
        2e-4,

    "max_length":
        512,

    "lora_r":
        8,

    "lora_alpha":
        16,

    "lora_dropout":
        0.05,

    "warmup_steps":
        100,

    "output_dir":
        "/kaggle/working/pharma_bot_v1",
}


print("=" * 60)
print("CONFIGURATION")
print("=" * 60)

for key, value in CONFIG.items():

    print(
        f"{key}: {value}"
    )
"""))


# ============================================================
# CELLULE 8
# TOKENIZER
# ============================================================

cells.append(code("""
#@title 7. Charger le tokenizer

from transformers import AutoTokenizer

print(
    "Chargement du tokenizer..."
)


tokenizer = AutoTokenizer.from_pretrained(

    CONFIG["base_model"],

    trust_remote_code=True
)


if tokenizer.pad_token is None:

    tokenizer.pad_token = (
        tokenizer.eos_token
    )


tokenizer.padding_side = "right"


print()
print(
    "Pad token :",
    tokenizer.pad_token
)

print(
    "EOS token :",
    tokenizer.eos_token
)

print()
print("✅ Tokenizer chargé.")
"""))


# ============================================================
# CELLULE 9
# MODELE QLORA
# ============================================================

cells.append(code("""
#@title 8. Charger TinyLlama avec QLoRA

import torch

from transformers import (
    AutoModelForCausalLM,
    BitsAndBytesConfig
)

from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training
)


print("=" * 60)
print("CHARGEMENT DU MODELE QLORA")
print("=" * 60)


# ------------------------------------------------------------
# BitsAndBytes
# ------------------------------------------------------------

bnb_config = BitsAndBytesConfig(

    load_in_4bit=True,

    bnb_4bit_quant_type="nf4",

    bnb_4bit_compute_dtype=
        torch.float16,

    bnb_4bit_use_double_quant=True,
)


# ------------------------------------------------------------
# Modèle
# ------------------------------------------------------------

model = AutoModelForCausalLM.from_pretrained(

    CONFIG["base_model"],

    quantization_config=bnb_config,

    torch_dtype=torch.float16,

    device_map={
        "": 0
    },

    trust_remote_code=True,
)


print(
    "Modèle de base chargé."
)


# ------------------------------------------------------------
# Préparer QLoRA
# ------------------------------------------------------------

model = prepare_model_for_kbit_training(
    model
)


# ------------------------------------------------------------
# LoRA
# ------------------------------------------------------------

lora_config = LoraConfig(

    r=CONFIG["lora_r"],

    lora_alpha=
        CONFIG["lora_alpha"],

    target_modules=[
        "q_proj",
        "v_proj"
    ],

    lora_dropout=
        CONFIG["lora_dropout"],

    bias="none",

    task_type="CAUSAL_LM",
)


model = get_peft_model(

    model,

    lora_config
)


# ------------------------------------------------------------
# Gradient checkpointing
# ------------------------------------------------------------

model.gradient_checkpointing_enable(

    gradient_checkpointing_kwargs={
        "use_reentrant": False
    }
)

model.config.use_cache = False


print()
print("=" * 60)
print("PARAMETRES ENTRAINABLES")
print("=" * 60)

model.print_trainable_parameters()


print()
print("GPU utilisé :")
print(
    torch.cuda.get_device_name(0)
)

print()
print("✅ Modèle QLoRA prêt.")
"""))


# ============================================================
# CELLULE 10
# TOKENISATION
# ============================================================

cells.append(code("""
#@title 9. Tokeniser les données

print("=" * 60)
print("TOKENISATION")
print("=" * 60)


def messages_to_text(example):

    # --------------------------------------------------------
    # Format Chat
    # --------------------------------------------------------

    if "messages" in example:

        messages = example["messages"]

        try:

            return tokenizer.apply_chat_template(

                messages,

                tokenize=False,

                add_generation_prompt=False
            )

        except Exception:

            parts = []

            for message in messages:

                role = message.get(
                    "role",
                    "user"
                )

                content = message.get(
                    "content",
                    ""
                )

                parts.append(
                    f"{role}: {content}"
                )

            return "\\n".join(parts)


    # --------------------------------------------------------
    # Format question / answer
    # --------------------------------------------------------

    if (
        "question" in example
        and "answer" in example
    ):

        return (
            "Utilisateur: "
            + str(example["question"])
            + "\\nAssistant: "
            + str(example["answer"])
        )


    # --------------------------------------------------------
    # Format instruction / output
    # --------------------------------------------------------

    if (
        "instruction" in example
        and "output" in example
    ):

        return (
            "Instruction: "
            + str(example["instruction"])
            + "\\nRéponse: "
            + str(example["output"])
        )


    # --------------------------------------------------------
    # Format input / output
    # --------------------------------------------------------

    if (
        "input" in example
        and "output" in example
    ):

        return (
            "Utilisateur: "
            + str(example["input"])
            + "\\nAssistant: "
            + str(example["output"])
        )


    raise ValueError(
        "Structure du dataset non reconnue. "
        f"Colonnes trouvées : {list(example.keys())}"
    )


def prepare_text(example):

    return {
        "text":
            messages_to_text(example)
    }


train_dataset = train_dataset.map(
    prepare_text
)

val_dataset = val_dataset.map(
    prepare_text
)


print()
print("Exemple de texte :")
print(
    train_dataset[0]["text"]
)
"""))


# ============================================================
# CELLULE 11
# TOKENISATION FINALE
# ============================================================

cells.append(code("""
#@title 10. Tokenisation finale

def tokenize_function(example):

    tokens = tokenizer(

        example["text"],

        truncation=True,

        max_length=
            CONFIG["max_length"],

        padding="max_length"
    )


    tokens["labels"] = (
        tokens["input_ids"].copy()
    )


    return tokens


train_ds = train_dataset.map(

    tokenize_function,

    batched=False,

    remove_columns=
        train_dataset.column_names
)


val_ds = val_dataset.map(

    tokenize_function,

    batched=False,

    remove_columns=
        val_dataset.column_names
)


print("=" * 60)
print("TOKENISATION TERMINEE")
print("=" * 60)

print(
    "Train :",
    len(train_ds)
)

print(
    "Validation :",
    len(val_ds)
)

print(
    "Colonnes :",
    train_ds.column_names
)

print()
print("✅ Données prêtes pour Trainer.")
"""))


# ============================================================
# CELLULE 12
# TRAINER
# ============================================================

cells.append(code("""
#@title 11. Configurer Trainer

from transformers import (
    DataCollatorForLanguageModeling,
    TrainingArguments,
    Trainer
)


print("=" * 60)
print("CONFIGURATION TRAINER")
print("=" * 60)


import inspect

# Selon la version de transformers installée, certains arguments n'existent
# plus (ex : save_safetensors retiré en 2026). On filtre dynamiquement pour
# rester compatible avec toutes les versions.
args_kwargs = {

    "output_dir":
        CONFIG["output_dir"],

    "num_train_epochs":
        CONFIG["epochs"],

    "per_device_train_batch_size":
        CONFIG["batch_size"],

    "per_device_eval_batch_size":
        CONFIG["batch_size"],

    "gradient_accumulation_steps":
        CONFIG["gradient_accumulation"],

    "learning_rate":
        CONFIG["lr"],

    "warmup_steps":
        CONFIG["warmup_steps"],

    "weight_decay": 0.01,

    "logging_steps": 10,

    "eval_strategy": "epoch",

    "save_strategy": "epoch",

    "save_total_limit": 2,

    "load_best_model_at_end": True,

    "report_to": "none",

    "fp16": True,

    "bf16": False,

    "gradient_checkpointing": True,

    "gradient_checkpointing_kwargs": {
        "use_reentrant": False
    },

    "dataloader_num_workers": 2,

    "optim": "paged_adamw_8bit",

    "remove_unused_columns": False,
}

_args_valides = set(
    inspect.signature(
        TrainingArguments.__init__
    ).parameters
)

args_kwargs = {
    cle: valeur
    for cle, valeur in args_kwargs.items()
    if cle in _args_valides
}

training_args = TrainingArguments(
    **args_kwargs
)


# Selon la version, le paramètre s'appelle tokenizer ou processing_class
try:
    data_collator = (
        DataCollatorForLanguageModeling(

            tokenizer=tokenizer,

            mlm=False
        )
    )
except TypeError:
    data_collator = (
        DataCollatorForLanguageModeling(

            processing_class=tokenizer,

            mlm=False
        )
    )


trainer = Trainer(

    model=model,

    args=training_args,

    train_dataset=train_ds,

    eval_dataset=val_ds,

    data_collator=data_collator
)


print()
print("GPU :")
print(
    torch.cuda.get_device_name(0)
)

print()
print("Batch :", CONFIG["batch_size"])

print(
    "Accumulation :",
    CONFIG["gradient_accumulation"]
)

print(
    "Batch effectif :",
    CONFIG["batch_size"]
    * CONFIG["gradient_accumulation"]
)

print()
print("✅ Trainer prêt.")
"""))


# ============================================================
# CELLULE 13
# ENTRAINEMENT
# ============================================================

cells.append(code("""
#@title 12. Lancer l'entraînement

import torch

print("=" * 60)
print("DEBUT DE L'ENTRAINEMENT")
print("=" * 60)

print()
print(
    "GPU :",
    torch.cuda.get_device_name(0)
)

print(
    "VRAM totale :",
    round(
        torch.cuda.get_device_properties(0)
        .total_memory
        / (1024 ** 3),
        2
    ),
    "Go"
)

print()
print(
    "Nombre d'exemples train :",
    len(train_ds)
)

print(
    "Nombre d'exemples validation :",
    len(val_ds)
)

print()
print(
    "Nombre d'epochs :",
    CONFIG["epochs"]
)

print()
print("🚀 Entraînement en cours...")


train_result = trainer.train()


print()
print("=" * 60)
print("ENTRAINEMENT TERMINE")
print("=" * 60)

print()
print(
    "Loss finale :",
    train_result.training_loss
)
"""))


# ============================================================
# CELLULE 14
# SAUVEGARDE
# ============================================================

cells.append(code("""
#@title 13. Sauvegarder le modèle

import json
import os


output_dir = CONFIG["output_dir"]


os.makedirs(
    output_dir,
    exist_ok=True
)


print(
    "Sauvegarde du modèle..."
)


# ------------------------------------------------------------
# Adapter LoRA
# ------------------------------------------------------------

trainer.save_model(
    output_dir
)


# ------------------------------------------------------------
# Tokenizer
# ------------------------------------------------------------

tokenizer.save_pretrained(
    output_dir
)


# ------------------------------------------------------------
# Informations
# ------------------------------------------------------------

training_info = {

    "base_model":
        CONFIG["base_model"],

    "epochs":
        CONFIG["epochs"],

    "batch_size":
        CONFIG["batch_size"],

    "gradient_accumulation":
        CONFIG["gradient_accumulation"],

    "learning_rate":
        CONFIG["lr"],

    "max_length":
        CONFIG["max_length"],

    "lora_r":
        CONFIG["lora_r"],

    "lora_alpha":
        CONFIG["lora_alpha"],

    "lora_dropout":
        CONFIG["lora_dropout"],

    "train_size":
        len(train_ds),

    "val_size":
        len(val_ds),

    "gpu":
        torch.cuda.get_device_name(0)
}


with open(

    os.path.join(
        output_dir,
        "training_info.json"
    ),

    "w",

    encoding="utf-8"

) as f:

    json.dump(

        training_info,

        f,

        ensure_ascii=False,

        indent=2
    )


print()
print("=" * 60)
print("MODELE SAUVEGARDE")
print("=" * 60)

print()
print(
    "Dossier :",
    output_dir
)

print()
print("✅ Sauvegarde terminée.")
"""))


# ============================================================
# CELLULE 15
# ZIP
# ============================================================

cells.append(code("""
#@title 14. Créer le ZIP final

import shutil
import os


zip_base = (
    "/kaggle/working/"
    "pharma_bot_v1"
)


zip_path = shutil.make_archive(

    zip_base,

    "zip",

    CONFIG["output_dir"]
)


print("=" * 60)
print("ZIP FINAL")
print("=" * 60)

print()
print(
    "ZIP :",
    zip_path
)

print()
print(
    "Taille :",
    round(
        os.path.getsize(zip_path)
        / (1024 ** 2),
        2
    ),
    "Mo"
)

print()
print("✅ Modèle prêt à être récupéré.")
"""))


# ============================================================
# CREATION DU NOTEBOOK
# ============================================================

nb = {

    "nbformat": 4,

    "nbformat_minor": 5,

    "metadata": {

        "kernelspec": {

            "display_name":
                "Python 3",

            "language":
                "python",

            "name":
                "python3"
        },

        "language_info": {

            "name":
                "python",

            "version":
                "3.12"
        }
    },

    "cells":
        cells
}


# ============================================================
# CREER LE DOSSIER
# ============================================================

os.makedirs(

    os.path.dirname(OUT),

    exist_ok=True
)


# ============================================================
# ECRIRE LE NOTEBOOK
# ============================================================

with open(

    OUT,

    "w",

    encoding="utf-8"

) as f:

    json.dump(

        nb,

        f,

        ensure_ascii=False,

        indent=1
    )


# ============================================================
# VALIDATION DU NOTEBOOK
# ============================================================

print()
print("=" * 60)
print("VALIDATION DU NOTEBOOK")
print("=" * 60)


# Vérifier que le JSON est valide
with open(
    OUT,
    "r",
    encoding="utf-8"
) as f:

    test_nb = json.load(f)


print("✓ JSON valide")


# Vérifier que les cellules Python compilent
code_cells = [
    cell
    for cell in test_nb["cells"]
    if cell["cell_type"] == "code"
]


errors = []


for index, cell in enumerate(
    code_cells,
    start=1
):

    source = "".join(
        cell["source"]
    )

    # Ignorer les magics IPython (!pip, %time, ...) : non parsables en Python pur
    # (une commande shell peut s'étendre sur plusieurs lignes via des backslash)
    lignes_python = []
    en_continuation = False

    for ligne in source.split("\n"):

        if en_continuation:
            en_continuation = ligne.rstrip().endswith("\\")
            continue

        if ligne.lstrip().startswith(("!", "%")):
            en_continuation = ligne.rstrip().endswith("\\")
            continue

        lignes_python.append(ligne)

    try:

        ast.parse(
            "\n".join(lignes_python)
        )

    except SyntaxError as e:
        errors.append(
            f"Cellule {index}: {e}"
        )


if errors:

    print()
    print("❌ ERREURS DE SYNTAXE")

    for error in errors:
        print(error)

    raise RuntimeError(
        "Le notebook contient des erreurs."
    )


print("✓ Toutes les cellules Python compilent")


# ============================================================
# RESULTAT
# ============================================================

print()
print("=" * 60)
print("NOTEBOOK KAGGLE CREE AVEC SUCCES")
print("=" * 60)

print()
print("Fichier :")
print(OUT)

print()
print(
    "Nombre de cellules :",
    len(cells)
)

print()
print("Configuration :")
print("✓ TinyLlama 1.1B")
print("✓ QLoRA 4-bit NF4")
print("✓ LoRA r=8")
print("✓ LoRA alpha=16")
print("✓ GPU T4")
print("✓ Détection automatique du dataset")
print("✓ train.json / val.json")
print("✓ Dataset JSON unique")
print("✓ Split validation automatique")
print("✓ Chat template")
print("✓ Gradient checkpointing")
print("✓ use_reentrant=False")
print("✓ warmup_steps")
print("✓ paged_adamw_8bit")
print("✓ Sauvegarde LoRA")
print("✓ ZIP final")

print()
print("👉 Importe ce fichier dans Kaggle :")
print(OUT)
