import json
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "stock.json")

def load_stock():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_stock(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def calculer_cmm(stock_debut, stock_fin):
    return max(0, stock_debut - stock_fin)

def calculer_ss(cmm, delai_livraison_jours):
    return 0.5 * cmm * (delai_livraison_jours / 30)

def calculer_smin(ss, cmm, delai_livraison_jours):
    return ss + (cmm * delai_livraison_jours / 30)

def calculer_smax(sr, smin):
    return sr + smin

def calculer_qac(smax, stock_disponible):
    return max(0, smax - stock_disponible)

def calculer_sr(cmm, delai_livraison_jours):
    return cmm * (delai_livraison_jours / 30)

def analyser_produit(nom, stock_actuel, cmm, delai_livraison_jours):
    sr = calculer_sr(cmm, delai_livraison_jours)
    ss = calculer_ss(cmm, delai_livraison_jours)
    smin = calculer_smin(ss, cmm, delai_livraison_jours)
    smax = calculer_smax(sr, smin)
    qac = calculer_qac(smax, stock_actuel)

    statut = "OK"
    if stock_actuel <= ss:
        statut = "RUPTURE IMMINENTE"
    elif stock_actuel <= smin:
        statut = "COMMANDE URGENTE"
    elif stock_actuel <= smax:
        statut = "A COMMANDER"

    return {
        "nom": nom,
        "stock_actuel": stock_actuel,
        "cmm": round(cmm, 2),
        "sr": round(sr, 2),
        "ss": round(ss, 2),
        "smin": round(smin, 2),
        "smax": round(smax, 2),
        "qac": round(qac, 2),
        "statut": statut
    }

def ajouter_produit(nom, stock_actuel, cmm, delai_livraison_jours):
    data = load_stock()
    data[nom] = {
        "stock_actuel": stock_actuel,
        "cmm": cmm,
        "delai_livraison_jours": delai_livraison_jours,
        "date_ajout": datetime.now().isoformat()
    }
    save_stock(data)
    return analyser_produit(nom, stock_actuel, cmm, delai_livraison_jours)

def lister_produits():
    data = load_stock()
    resultats = []
    for nom, info in data.items():
        resultat = analyser_produit(
            nom, info["stock_actuel"], info["cmm"], info["delai_livraison_jours"]
        )
        resultats.append(resultat)
    return resultats

def get_alertes():
    produits = lister_produits()
    return [p for p in produits if p["statut"] != "OK"]

def get_commandes():
    produits = lister_produits()
    return [p for p in produits if p["qac"] > 0]

def supprimer_produit(nom):
    data = load_stock()
    if nom in data:
        del data[nom]
        save_stock(data)
        return True
    return False

def modifier_stock(nom, nouveau_stock):
    data = load_stock()
    if nom in data:
        data[nom]["stock_actuel"] = nouveau_stock
        save_stock(data)
        return analyser_produit(nom, nouveau_stock, data[nom]["cmm"], data[nom]["delai_livraison_jours"])
    return None
