KNOWLEDGE = {
    "etapes_gestion": {
        "question": "Quelles sont les étapes de base de gestion dans tout système d'approvisionnement en médicaments ?",
        "reponse": """Les étapes de base sont :
1. La sélection des médicaments
2. L'acquisition / stockage (Réception / Stockage)
3. La distribution
4. L'utilisation"""
    },
    "avant_commande": {
        "question": "Que faut-il préciser avant d'établir une commande de médicaments ?",
        "reponse": "Il faut au préalable préciser la date et le rythme des commandes (quand faut-il commander)."
    },
    "methodes_estimation": {
        "question": "Quelles sont les deux méthodes d'estimation des besoins pour établir une commande ?",
        "reponse": """1. La méthode d'estimation basée sur les morbidités
2. La méthode d'estimation des besoins basée sur la consommation antérieure"""
    },
    "calcul_cmm": {
        "question": "Comment est calculée la Consommation Moyenne Mensuelle (CMM) ?",
        "reponse": "En se basant sur les fiches de stock."
    },
    "formule_cmm": {
        "question": "Quelle est la formule pour calculer la CMM ?",
        "reponse": "CMM = Stock début de mois - Stock fin de mois"
    },
    "stock_roulement": {
        "question": "Qu'est-ce que le Stock de Roulement (SR) ?",
        "reponse": "Il s'agit du stock pour satisfaire la demande entre les livraisons, il doit tenir compte de la périodicité et du délai de livraison."
    },
    "stock_securite": {
        "question": "Qu'est-ce que le Stock de Sécurité (SS) ?",
        "reponse": "C'est une réserve qui permet de parer aux ruptures de stock, elle correspond à la moitié de consommation entre deux commandes. Il fixe le seuil en dessous duquel le stock disponible ne doit jamais descendre."
    },
    "stock_minimum": {
        "question": "Qu'est-ce que le Stock Minimum (SMin) ?",
        "reponse": "C'est le stock définissant le point de commande pour couvrir les délais d'approvisionnement et le stock de sécurité. Si le stock restant est égal au stock minimum, il faut lancer la commande."
    },
    "stock_maximum": {
        "question": "Qu'est-ce que le Stock Maximum (SMax) ?",
        "reponse": "Il est égal au stock de roulement ajouté au stock minimum."
    },
    "formule_qac": {
        "question": "Quelle est la formule pour calculer la Quantité A Commander (QAC) ?",
        "reponse": "QAC = Stock Maximum - Stock Disponible"
    },
    "formule_smax": {
        "question": "Quelle est la formule du Stock Maximum ?",
        "reponse": "SMax = Stock de Roulement + Stock Minimum"
    },
    "formule_smin": {
        "question": "Quelle est la formule du Stock Minimum ?",
        "reponse": "SMin = Stock de Sécurité + (CMM × Délai de livraison / 30)"
    },
    "formule_ss": {
        "question": "Quelle est la formule du Stock de Sécurité ?",
        "reponse": "SS = 0.5 × CMM × (Délai de livraison / 30)"
    },
    "formule_sr": {
        "question": "Quelle est la formule du Stock de Roulement ?",
        "reponse": "SR = CMM × (Délai de livraison / 30)"
    }
}

def rechercher(requete):
    requete_lower = requete.lower()
    resultats = []
    mots_cles = requete_lower.split()
    
    for cle, entry in KNOWLEDGE.items():
        score = 0
        text = (entry["question"] + " " + entry["reponse"]).lower()
        for mot in mots_cles:
            if mot in text:
                score += 1
        if score > 0:
            resultats.append((score, entry))
    
    resultats.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in resultats]

def get_all_questions():
    return [entry["question"] for entry in KNOWLEDGE.values()]
