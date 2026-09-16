#!/usr/bin/env python3
"""
kaggle_gpu.py — Entraîner l'IA du projet sur les GPU gratuits de Kaggle.

Le pipeline complet :

    1. prepare   → (re)génère train.json / val.json, copie les données dans
                   kaggle_submission/ et écrit les métadonnées dataset + notebook
    2. push      → crée/met à jour le dataset Kaggle, puis pousse le notebook
                   (GPU T4 + internet activés) ; Kaggle lance l'entraînement
    3. status    → suit l'avancement de la session GPU (--wait pour attendre)
    4. output    → télécharge le modèle LoRA entraîné dans ml/models/

Exemple :

    python3 scripts/kaggle_gpu.py check
    python3 scripts/kaggle_gpu.py all --wait
    python3 scripts/kaggle_gpu.py output

Authentification (une seule fois) — au choix :
    - `kaggle auth login`              (OAuth, recommandé)
    - KAGGLE_API_TOKEN=<token>         (https://www.kaggle.com/settings/api)
    - ~/.kaggle/kaggle.json            (format classique {username, key})
    - ~/.kaggle/access_token           (token API brut)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KAGGLE_DIR = os.path.join(PROJECT_ROOT, "kaggle_submission")
NOTEBOOK = os.path.join(PROJECT_ROOT, "ml", "notebooks", "kaggle_train.ipynb")
GENERATOR = os.path.join(PROJECT_ROOT, "scripts", "generate_kaggle_notebook.py")
DATA_DIR = os.path.join(PROJECT_ROOT, "ml", "data")
MODELS_DIR = os.path.join(PROJECT_ROOT, "ml", "models")

CONFIG_PATH = os.path.join(KAGGLE_DIR, "kaggle_config.json")
DATASET_META = os.path.join(KAGGLE_DIR, "dataset-metadata.json")
KERNEL_META = os.path.join(KAGGLE_DIR, "kernel-metadata.json")

# Statuts possibles d'une session de notebook Kaggle
STATUS_RUNNING = {"queued", "running", "cancelRequested", "cancelAcknowledged"}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ============================================================
# Configuration
# ============================================================

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_username(config):
    """Trouve le nom d'utilisateur Kaggle (config, env ou ~/.kaggle/kaggle.json)."""
    username = config.get("kaggle_username") or ""
    if username and "REMPLACE" not in username.upper():
        return username

    username = os.environ.get("KAGGLE_USERNAME", "")
    if username:
        return username

    kaggle_json = os.path.join(os.path.expanduser("~"), ".kaggle", "kaggle.json")
    if os.path.exists(kaggle_json):
        with open(kaggle_json, "r", encoding="utf-8") as f:
            return json.load(f).get("username", "")

    return None


def has_credentials():
    """Vérifie qu'un vrai token Kaggle est disponible (username seul ne suffit pas)."""
    if os.environ.get("KAGGLE_API_TOKEN"):
        return True
    kaggle_dir = os.path.join(os.path.expanduser("~"), ".kaggle")
    if not os.path.isdir(kaggle_dir):
        return False
    # access_token doit être non vide pour compter
    token = os.path.join(kaggle_dir, "access_token")
    if os.path.exists(token) and os.path.getsize(token) > 2:
        return True
    return any(
        os.path.exists(os.path.join(kaggle_dir, name))
        for name in ("kaggle.json", "credentials")
    )


def _silent_import_kaggle():
    """Importe la lib kaggle sans son banner d'authentification intempestif."""
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        import kaggle

    return kaggle


def need_username(config):
    username = resolve_username(config)
    if not username:
        sys.exit(
            "\n❌ Nom d'utilisateur Kaggle inconnu.\n"
            "   Ajoute-le dans kaggle_submission/kaggle_config.json (champ \"kaggle_username\"),\n"
            "   ou lance `kaggle auth login`, ou renseigne KAGGLE_USERNAME.\n"
        )
    return username


# ============================================================
# Commandes
# ============================================================

def cmd_check(config):
    log("Vérification de l'environnement Kaggle...")

    ok = True

    # 1. Authentification
    if has_credentials():
        print("  ✅ Identifiants Kaggle trouvés (env ou ~/.kaggle)")
    else:
        print("  ❌ Aucun identifiant Kaggle.")
        print("     → kaggle auth login  (ou ~/.kaggle/kaggle.json, ou KAGGLE_API_TOKEN)")
        ok = False

    # 2. Bibliothèque kaggle
    try:
        _silent_import_kaggle()
        print("  ✅ Bibliothèque `kaggle` importée")
    except Exception as e:
        print(f"  ❌ Bibliothèque `kaggle` indisponible : {e}")
        print("     → .venv/bin/pip install kaggle")
        ok = False

    # 3. Données d'entraînement
    train = os.path.join(KAGGLE_DIR, "train.json")
    val = os.path.join(KAGGLE_DIR, "val.json")
    if os.path.exists(train) and os.path.exists(val):
        n_train = len(json.load(open(train, encoding="utf-8")))
        n_val = len(json.load(open(val, encoding="utf-8")))
        print(f"  ✅ Données prêtes : {n_train} train / {n_val} val")
    else:
        print("  ⚠️  train.json / val.json absents de kaggle_submission/ → lance `prepare`")

    # 4. Notebook
    if os.path.exists(NOTEBOOK):
        try:
            with open(NOTEBOOK, encoding="utf-8") as f:
                nb = json.load(f)
            cells = len(nb.get("cells", []))
            print(f"  ✅ Notebook Kaggle valide ({cells} cellules)")
        except Exception as e:
            print(f"  ❌ Notebook illisible : {e}")
            ok = False
    else:
        print("  ⚠️  Notebook absent → python3 scripts/generate_kaggle_notebook.py")

    # 5. Métadonnées
    for path, name in ((DATASET_META, "dataset-metadata.json"), (KERNEL_META, "kernel-metadata.json")):
        if os.path.exists(path):
            print(f"  ✅ {name} présent")
        else:
            print(f"  ⚠️  {name} absent → lance `prepare`")

    if resolve_username(config):
        print(f"  ✅ Utilisateur Kaggle : {resolve_username(config)}")
    else:
        print("  ⚠️  kaggle_username non renseigné dans kaggle_config.json")

    print()
    if ok:
        print("✅ Prêt. Lance : python3 scripts/kaggle_gpu.py push")
    else:
        print("❌ Corrige les points ci-dessus avant de continuer.")
        sys.exit(1)


def cmd_prepare(config):
    username = need_username(config)
    dataset_slug = config["dataset_slug"]
    notebook_slug = config["notebook_slug"]

    log("Préparation des données d'entraînement...")

    # 1. Générer train/val si absents
    if not os.path.exists(os.path.join(DATA_DIR, "train.json")):
        log("train.json absent → exécution de ml/src/preprocessing.py")
        subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, "ml", "src", "preprocessing.py")], check=True)

    # 2. Copier les données
    os.makedirs(KAGGLE_DIR, exist_ok=True)
    for name in ("train.json", "val.json"):
        shutil.copy2(os.path.join(DATA_DIR, name), os.path.join(KAGGLE_DIR, name))
    n_train = len(json.load(open(os.path.join(KAGGLE_DIR, "train.json"), encoding="utf-8")))
    n_val = len(json.load(open(os.path.join(KAGGLE_DIR, "val.json"), encoding="utf-8")))
    log(f"Données : {n_train} train / {n_val} val → {KAGGLE_DIR}")

    # 3. Régénérer le notebook si absent
    if not os.path.exists(NOTEBOOK):
        log("Génération du notebook...")
        subprocess.run([sys.executable, GENERATOR], check=True)

    # 4. Métadonnées dataset
    with open(DATASET_META, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title": config["dataset_title"],
                "id": f"{username}/{dataset_slug}",
                "licenses": [{"name": "CC0-1.0"}],
                "description": "Dataset d'entraînement du chatbot pharmacie (TinyLlama QLoRA).",
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # 5. Métadonnées notebook (GPU + internet activés)
    with open(KERNEL_META, "w", encoding="utf-8") as f:
        json.dump(
            {
                "id": f"{username}/{notebook_slug}",
                "title": config["notebook_title"],
                "code_file": "kaggle_train.ipynb",
                "language": "python",
                "kernel_type": "notebook",
                "is_private": True,
                "enable_gpu": True,
                "enable_internet": True,
                "machine_shape": config.get("machine_shape", "NvidiaTeslaT4"),
                "dataset_sources": [f"{username}/{dataset_slug}"],
                "keywords": ["pharmacy", "llm", "qlora"],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # 6. Copier le notebook dans kaggle_submission/ (code_file relatif au dossier)
    shutil.copy2(NOTEBOOK, os.path.join(KAGGLE_DIR, "kaggle_train.ipynb"))

    log("✅ Préparation terminée. Prochaine étape : python3 scripts/kaggle_gpu.py push")


def _api():
    _silent_import_kaggle()
    # Import explicite du sous-module : `kaggle.api` est une instance pré-créée
    # dans kaggle 2.x, pas un module.
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    return api


def _python():
    """Interpréteur Python disposant de la bibliothèque kaggle (le venv en priorité)."""
    candidates = [
        os.path.join(PROJECT_ROOT, ".venv", "bin", "python"),
        sys.executable,
        "python3",
    ]
    for py in candidates:
        try:
            subprocess.run([py, "-c", "import kaggle"], check=True, capture_output=True)
            return py
        except subprocess.CalledProcessError:
            continue
    return sys.executable


def cmd_push(config):
    username = need_username(config)
    ref_dataset = f"{username}/{config['dataset_slug']}"
    ref_kernel = f"{username}/{config['notebook_slug']}"
    api = _api()
    ignore = ["*.ipynb", "dataset-metadata.json", "kernel-metadata.json", "kaggle_config.json"]

    # 1. Dataset : on tente la création d'abord. Si le titre est déjà pris,
    # le dataset existe → on pousse une nouvelle version. (On évite ainsi
    # dataset_status, permission non couverte par certains tokens KGAT.)
    log(f"Dataset {ref_dataset}...")
    resp = api.dataset_create_new(KAGGLE_DIR, ignore_patterns=ignore)
    status = getattr(resp, "status", "") or ""
    if status == "error":
        err = getattr(resp, "error", "") or ""
        if "in use" in err.lower():
            log("Dataset existant → nouvelle version...")
            api.dataset_create_version(
                KAGGLE_DIR,
                version_notes=f"MAJ données {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                ignore_patterns=ignore,
            )
        else:
            sys.exit(f"\n❌ Erreur création dataset : {err}\n")
    else:
        log("Dataset créé.")

    # Kaggle traite l'upload en arrière-plan ; le push du notebook qui y fait
    # référence juste après peut échouer si le dataset n'est pas encore prêt.
    log("Attente de la disponibilité du dataset (30 s)...")
    time.sleep(30)

    # 2. Notebook : push (déclenche automatiquement une session GPU)
    log(f"Push du notebook {ref_kernel} (GPU {config.get('machine_shape', 'NvidiaTeslaT4')})...")
    api.kernels_push(KAGGLE_DIR)

    print()
    log("✅ Entraînement envoyé sur Kaggle !")
    print(f"    Suivi : https://www.kaggle.com/code/{username}/{config['notebook_slug']}")
    print("    (l'entraînement démarre automatiquement, compte ~15-40 min sur T4)")
    print()
    print("    python3 scripts/kaggle_gpu.py status --wait   # attendre la fin")
    print("    python3 scripts/kaggle_gpu.py output          # récupérer le modèle")


def _session_log(api, ref_kernel):
    """Télécharge le log de session via kernels_output (marche sans kernels.get)."""
    import tempfile

    tmp = tempfile.mkdtemp(prefix="kaggle_log_")
    try:
        files, _ = api.kernels_output(ref_kernel, tmp)
        for name in files:
            if name.endswith(".log"):
                return os.path.join(tmp, os.path.basename(name))
    except Exception:
        pass
    return None


def _parse_log_status(log_path):
    """Déduit l'état de l'entraînement depuis le log de session Kaggle."""
    if not log_path or not os.path.exists(log_path):
        return None
    with open(log_path, encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if "Modèle prêt à être récupéré" in content:
        return "complete"
    if "PapermillExecutionError" in content or "Exception encountered at" in content:
        return "error"
    if "ENTRAINEMENT TERMINE" in content:
        return "complete"
    if "DEBUT DE L'ENTRAINEMENT" in content or "Entraînement en cours" in content:
        return "training"
    return "running"


def cmd_status(config, wait=False, timeout=7200):
    username = need_username(config)
    ref_kernel = f"{username}/{config['notebook_slug']}"
    api = _api()

    start = time.time()
    while True:
        # API officielle (peut être refusée par certains tokens KGAT),
        # sinon on déduit l'état du log de session téléchargé via kernels_output.
        try:
            status_obj = api.kernels_status(ref_kernel)
            status = getattr(status_obj, "status", str(status_obj))
        except Exception:
            status = _parse_log_status(_session_log(api, ref_kernel))

        if status == "complete":
            log("✅ Entraînement terminé ! Récupère le modèle : python3 scripts/kaggle_gpu.py output")
            return "complete"
        if status == "error":
            log("❌ Entraînement en erreur — regarde les logs sur Kaggle :")
            print(f"    https://www.kaggle.com/code/{username}/{config['notebook_slug']}")
            return "error"

        if not wait:
            log(f"Statut : {status}")
            return status

        elapsed = int(time.time() - start)
        if elapsed > timeout:
            log(f"⏱️  Timeout ({timeout}s écoulés), statut toujours : {status}")
            return status

        log(f"Statut : {status} — encore {int(timeout - elapsed)}s de timeout ({elapsed}s écoulés)")
        time.sleep(30)


def cmd_output(config):
    username = need_username(config)
    ref_kernel = f"{username}/{config['notebook_slug']}"
    api = _api()

    out_dir = os.path.join(MODELS_DIR, "kaggle_output")
    os.makedirs(out_dir, exist_ok=True)

    log(f"Téléchargement de la sortie de {ref_kernel}...")
    files, _token = api.kernels_output(ref_kernel, out_dir)
    for f in files:
        print(f"    • {f}")

    # Décompresser l'adapter LoRA dans ml/models/pharma_bot_v1/
    model_dir = os.path.join(MODELS_DIR, "pharma_bot_v1")
    zip_path = os.path.join(out_dir, "pharma_bot_v1.zip")
    if os.path.exists(zip_path):
        log(f"Décompression de {zip_path} → {model_dir}")
        os.makedirs(model_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(model_dir)
        log("✅ Modèle LoRA prêt :")
        print(f"    python3 ml/src/predict.py --model {os.path.relpath(model_dir, PROJECT_ROOT)}")
    else:
        log("⚠️  pharma_bot_v1.zip introuvable dans la sortie (entraînement terminé ?)")


def cmd_all(config, wait=False, timeout=7200):
    cmd_prepare(config)
    cmd_push(config)
    if wait:
        cmd_status(config, wait=True, timeout=timeout)


# ============================================================
# Point d'entrée
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Entraîner l'IA pharmacie sur les GPU gratuits de Kaggle.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "command",
        choices=["check", "prepare", "push", "status", "output", "all"],
        help="check: vérifier l'env | prepare: données + métadonnées | push: envoyer sur Kaggle | "
             "status: suivi | output: récupérer le modèle | all: prepare + push",
    )
    parser.add_argument("--wait", action="store_true", help="status : attendre la fin de l'entraînement")
    parser.add_argument("--timeout", type=int, default=7200, help="status --wait : timeout en secondes (défaut 7200)")
    args = parser.parse_args()

    # check et prepare sont 100% locaux : pas besoin d'identifiants.
    # push / status / output contactent l'API → token obligatoire.
    if args.command in ("push", "status", "output", "all") and not has_credentials():
        print(
            "\n❌ Aucun identifiant Kaggle détecté.\n\n"
            "   Une seule fois :\n"
            "     kaggle auth login              # OAuth (recommandé)\n"
            "   ou :\n"
            "     export KAGGLE_API_TOKEN=xxx    # https://www.kaggle.com/settings/api\n"
            "   ou :\n"
            "     ~/.kaggle/kaggle.json          # {\"username\": \"...\", \"key\": \"...\"}\n"
        )
        sys.exit(1)

    config = load_config()

    if args.command == "check":
        cmd_check(config)
    elif args.command == "prepare":
        cmd_prepare(config)
    elif args.command == "push":
        cmd_push(config)
    elif args.command == "status":
        cmd_status(config, wait=args.wait, timeout=args.timeout)
    elif args.command == "output":
        cmd_output(config)
    elif args.command == "all":
        cmd_all(config, wait=args.wait, timeout=args.timeout)


if __name__ == "__main__":
    # La bibliothèque kaggle vit souvent dans .venv ; on se ré-exécute avec
    # le bon interpréteur avant de faire quoi que ce soit.
    try:
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()):
            import kaggle  # noqa: F401
    except ImportError:
        _py = _python()
        if os.path.abspath(_py) != os.path.abspath(sys.executable):
            os.execv(_py, [_py, os.path.abspath(__file__), *sys.argv[1:]])
    main()
