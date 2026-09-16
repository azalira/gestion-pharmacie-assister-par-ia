# IA — Binôme 2 (Harilaza)

Fine-tuning d'un petit LLM (TinyLlama-1.1B) pour le chatbot pharmacien.

## Architecture

```
symptomes_db.py (64 medicaments)
        |
        v
preprocessing.py  --->  ml/data/{train,val}.json  (729 exemples)
        |
        v
train.py  (LoRA fine-tuning)
        |
        v
ml/models/pharma_bot_v1/  (poids LoRA)
        |
        +---> predict.py    (inference interactive ou batch)
        +---> evaluate.py   (metriques EM, F1, containment)
```

## Pourquoi TinyLlama-1.1B ?

- **1.1B parametres** (~1 Go en float32)
- **Fonctionne sur CPU** (lent mais possible), GPU recommande
- **Licence Apache 2.0** (usage commercial autorise)
- **Supporte chatml** (format standard pour l'instruction-tuning)
- Alternative : `microsoft/phi-2` (2.7B), `mistralai/Mistral-7B-v0.1` (plus gros, GPU obligatoire)

## Pipeline complete

```bash
# 1. Generer le dataset d'entrainement
python ml/src/preprocessing.py
# -> 729 exemples : 656 train, 73 val

# 2. Fine-tuner le modele (LoRA, ~30 min sur GPU, 1-2h sur CPU)
python ml/src/train.py --epochs 3 --batch-size 4
# -> Sortie : ml/models/pharma_bot_v1/

# 3. Tester en mode interactif
python ml/src/predict.py --model ml/models/pharma_bot_v1

# 4. Poser une question unique
python ml/src/predict.py --model ml/models/pharma_bot_v1 \
    --question "J'ai des vomissements, que prendre ?"

# 5. Evaluer sur le jeu de validation
python ml/src/evaluate.py --model ml/models/pharma_bot_v1 --limit 20
```

## Format des donnees

```json
{
  "messages": [
    {"role": "system", "content": "Tu es un assistant pharmacien..."},
    {"role": "user", "content": "Quels medicaments pour vomissement ?"},
    {"role": "assistant", "content": "Mugrucaine est un medicament..."}
  ]
}
```

Converti en chatml pour l'entrainement :
```
<|im_start|>system
Tu es un assistant pharmacien...<|im_end|>
<|im_start|>user
Quels medicaments pour vomissement ?<|im_end|>
<|im_start|>assistant
Mugrucaine est un medicament...<|im_end|>
```

## Hyperparametres par defaut

| Parametre        | Valeur         | Notes                                    |
|------------------|----------------|------------------------------------------|
| Modele de base   | TinyLlama-1.1B | Remplacable (Phi-2, Mistral, etc.)       |
| Methode          | LoRA           | r=8, alpha=16, dropout=0.05              |
| Learning rate    | 2e-4           | Standard pour LoRA                       |
| Batch size       | 2 + grad accum | 4 (effective)                            |
| Epochs           | 3              | Adapter selon surapprentissage           |
| Max length       | 512 tokens     | Suffisant pour la majorite des exemples  |
| Quantization     | Float32 (CPU)  | ou 4-bit (QLoRA sur GPU avec --qlora)    |

## Limites et ameliorations

### Limites actuelles
- **Donnees limitees** : 729 exemples generes depuis la base interne. Pas assez pour un modele LLM pret a la production.
- **Pas de validation medicale** : le modele peut halluciner. Toujours reaffirmer la necessite de consulter un professionnel.
- **Langue unique** : francais uniquement.

### Pour aller plus loin
1. **Augmenter les donnees** : utiliser PubMedQA, MedQuAD (anglais), ou des corpus francais equivalents.
2. **RLHF** : preference humaine sur les reponses medicales.
3. **RAG hybride** : coupler avec le systeme RAG existant (`backend/app/ia/rag/`) pour ancrer les reponses dans la base BDPM.
4. **Multi-tour** : entrainer sur des conversations completes (actuellement mono-tour + 3 exemples multi-tour).
5. **Quantization post-training** : GPTQ, AWQ pour inference rapide (CPU < 500ms par reponse).

## Dependances

```bash
pip install torch transformers datasets peft accelerate
# Optionnel (QLoRA) :
pip install bitsandbytes
# Entraînement distant sur GPU Kaggle :
pip install kaggle
```

## Entraînement sur les GPU Kaggle (sans GPU local)

Le pipeline distant est automatisé (données → dataset Kaggle → notebook GPU → récupération du modèle) :

```bash
kaggle auth login                              # une seule fois
python3 scripts/kaggle_gpu.py check            # diagnostic
python3 scripts/kaggle_gpu.py all --wait       # envoi + suivi de l'entraînement (T4)
python3 scripts/kaggle_gpu.py output           # modèle LoRA → ml/models/pharma_bot_v1/
```

Le notebook exécuté côté Kaggle est `ml/notebooks/kaggle_train.ipynb` (régénérable via
`python3 scripts/generate_kaggle_notebook.py`) ; il active GPU + Internet, charge le dataset
attaché, entraîne TinyLlama en QLoRA et produit `pharma_bot_v1.zip` en sortie.

## Fichiers

- `src/preprocessing.py` — generation du dataset depuis symptomes_db + knowledge_base
- `src/train.py` — LoRA fine-tuning avec HuggingFace Trainer
- `src/predict.py` — inference (interactif, question unique, batch)
- `src/evaluate.py` — metriques EM, F1, containment, latence
- `data/train.json` / `data/val.json` — jeu de donnees
- `data/train_chatml.jsonl` / `data/val_chatml.jsonl` — format chatml pour TRL
- `models/pharma_bot_v1/` — modele fine-tune (a generer avec train.py)
