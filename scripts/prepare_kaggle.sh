#!/usr/bin/env bash
# Préparation des données pour l'entraînement sur Kaggle GPU.
#
# Le pipeline complet est désormais automatisé par scripts/kaggle_gpu.py :
#
#     python3 scripts/kaggle_gpu.py check      # vérifier l'environnement
#     python3 scripts/kaggle_gpu.py prepare    # données + métadonnées
#     python3 scripts/kaggle_gpu.py push       # envoyer et lancer l'entraînement
#     python3 scripts/kaggle_gpu.py status     # suivre l'avancement
#     python3 scripts/kaggle_gpu.py output     # récupérer le modèle LoRA
#
# Ce script conserve la compatibilité : il délègue à kaggle_gpu.py.

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Préparation Kaggle (délégation à scripts/kaggle_gpu.py) ==="
echo
python3 "$PROJECT_ROOT/scripts/kaggle_gpu.py" prepare "$@"
