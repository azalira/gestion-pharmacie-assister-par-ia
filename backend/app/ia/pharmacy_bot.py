import torch
from transformers import XLNetTokenizer, XLNetModel
from knowledge_base import rechercher, KNOWLEDGE
import stock_manager
import bdpm_loader
import symptomes_db
from rag.retriever import rechercher as rag_rechercher

class PharmacyBot:
    def __init__(self):
        print("Chargement de XLNet...")
        self.tokenizer = XLNetTokenizer.from_pretrained("xlnet-base-cased")
        self.model = XLNetModel.from_pretrained("xlnet-base-cased")
        self.model.eval()
        print("XLNet charge !")
        print(f"Base BDPM : {bdpm_loader.count_medicaments()} specialites chargees")
        print(f"Base symptomes : {len(symptomes_db.SYMPTOMES_MEDIAMENTS)} medicaments references")
    
    def comprendre(self, texte):
        inputs = self.tokenizer(texte, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    
    def repondre(self, message):
        msg = message.lower().strip()
        
        if msg in ("quit", "exit", "q", "quitter"):
            return "Au revoir !", True
        
        if msg in ("help", "aide", "?"):
            return self.aide(), False
        
        if msg in ("stock", "stocks", "liste"):
            return self.lister_stocks(), False
        
        if msg in ("alerte", "alertes", "rupture"):
            return self.alertes(), False
        
        if msg in ("commande", "commandes", "commander"):
            return self.commandes(), False
        
        if msg.startswith("ajouter"):
            return self.ajouter(message), False
        
        if msg.startswith("supprimer") or msg.startswith("retirer"):
            return self.supprimer(message), False
        
        if msg.startswith("modifier"):
            return self.modifier(message), False
        
        if msg in ("formules", "formule"):
            return self.afficher_formules(), False
        
        if msg.startswith("calculer"):
            return self.calculer(message), False
        
        if msg.startswith("rechercher ") or msg.startswith("chercher ") or msg.startswith("medoc ") or msg.startswith("medicament "):
            return self.rechercher_medoc(message), False
        
        if msg.startswith("info ") or msg.startswith("infos "):
            return self.info_medoc(message), False
        
        if msg.startswith("symptome ") or msg.startswith("symptomes ") or msg.startswith("mal "):
            return self.rechercher_symptome(message), False
        
        if msg.startswith("pour ") or msg.startswith("contre ") or msg.startswith("traiter "):
            return self.rechercher_pour(message), False
        
        if msg in ("stats", "statistiques", "resume"):
            return self.statistiques(), False
        
        if msg in ("classes", "classes medicaments"):
            return self.lister_classes(), False
        
        if msg in ("symptomes list", "liste symptomes"):
            return self.lister_symptomes(), False
        
        if "?" in msg or msg.startswith("qu") or msg.startswith("comment") or msg.startswith("quel") or msg.startswith("quelle"):
            return self.rechercher_rag(message), False
        
        resultats_symptomes = symptomes_db.rechercher_par_symptome(msg)
        if resultats_symptomes:
            return self.formater_symptomes(resultats_symptomes, msg), False
        
        return self.rechercher_rag(message), False
    
    def aide(self):
        return """=== IA Pharmacie - Aide ===

Commandes stock :
  stock                 Afficher tous les stocks
  alertes               Voir les alertes de rupture
  commandes             Voir les produits a commander
  ajouter <nom> <stock> <cmm> <delai>
                        Ajouter un produit
  supprimer <nom>       Supprimer un produit
  modifier <nom> <stock> Mettre a jour le stock
  calculer <nom>        Calculer les stats d'un produit
  formules              Afficher les formules de calcul

Commandes BDPM :
  rechercher <nom>      Rechercher un medicament
  info <cis>            Info details d'un medicament
  stats                 Statistiques de la base

Recherche intelligente (RAG) :
  <question libre>      Posez une question !

Recherche par symptome :
  symptome <mot>        Chercher par symptome
  pour <maladie>        Quel medicament pour...
  classes               Liste des classes therapeutiques
  symptomes list        Liste des symptomes

Autre :
  help                  Afficher cette aide
  quit                  Quitter"""
    
    def lister_stocks(self):
        produits = stock_manager.lister_produits()
        if not produits:
            return "Aucun produit en stock."
        
        lignes = ["=== INVENTAIRE ===\n"]
        lignes.append(f"{'Produit':<20} {'Stock':>6} {'CMM':>6} {'SMin':>6} {'SMax':>6} {'QAC':>6} {'Statut'}")
        lignes.append("-" * 80)
        
        for p in produits:
            lignes.append(
                f"{p['nom']:<20} {p['stock_actuel']:>6.0f} {p['cmm']:>6.1f} "
                f"{p['smin']:>6.1f} {p['smax']:>6.1f} {p['qac']:>6.1f} {p['statut']}"
            )
        
        return "\n".join(lignes)
    
    def alertes(self):
        alertes = stock_manager.get_alertes()
        if not alertes:
            return "Aucune alerte. Tous les stocks sont OK."
        
        lignes = ["=== ALERTES ===\n"]
        for a in alertes:
            if a["statut"] == "RUPTURE IMMINENTE":
                lignes.append(f"!!! {a['nom']} - RUPTURE IMMINENTE (stock: {a['stock_actuel']}, SS: {a['ss']})")
            elif a["statut"] == "COMMANDE URGENTE":
                lignes.append(f"!!  {a['nom']} - COMMANDE URGENTE (stock: {a['stock_actuel']}, SMin: {a['smin']})")
            else:
                lignes.append(f"!   {a['nom']} - A COMMANDER (stock: {a['stock_actuel']}, SMax: {a['smax']})")
        
        return "\n".join(lignes)
    
    def commandes(self):
        commandes = stock_manager.get_commandes()
        if not commandes:
            return "Aucune commande necessaire."
        
        lignes = ["=== PRODUITS A COMMANDER ===\n"]
        lignes.append(f"{'Produit':<20} {'Stock':>6} {'SMax':>6} {'QAC':>6}")
        lignes.append("-" * 45)
        
        for c in commandes:
            lignes.append(f"{c['nom']:<20} {c['stock_actuel']:>6.0f} {c['smax']:>6.1f} {c['qac']:>6.1f}")
        
        return "\n".join(lignes)
    
    def ajouter(self, message):
        parts = message.split()
        if len(parts) < 5:
            return "Usage: ajouter <nom> <stock_actuel> <cmm> <delai_livraison_jours>"
        
        try:
            nom = parts[1]
            stock = float(parts[2])
            cmm = float(parts[3])
            delai = float(parts[4])
            
            resultat = stock_manager.ajouter_produit(nom, stock, cmm, delai)
            return f"Produit '{nom}' ajoute !\n{self.formater_analyse(resultat)}"
        except ValueError:
            return "Erreur: les valeurs numeriques sont invalides."
    
    def supprimer(self, message):
        parts = message.split()
        if len(parts) < 2:
            return "Usage: supprimer <nom>"
        
        nom = parts[1]
        if stock_manager.supprimer_produit(nom):
            return f"Produit '{nom}' supprime."
        return f"Produit '{nom}' non trouve."
    
    def modifier(self, message):
        parts = message.split()
        if len(parts) < 3:
            return "Usage: modifier <nom> <nouveau_stock>"
        
        try:
            nom = parts[1]
            nouveau_stock = float(parts[2])
            resultat = stock_manager.modifier_stock(nom, nouveau_stock)
            if resultat:
                return f"Stock de '{nom}' mis a jour !\n{self.formater_analyse(resultat)}"
            return f"Produit '{nom}' non trouve."
        except ValueError:
            return "Erreur: la valeur du stock est invalide."
    
    def afficher_formules(self):
        return """=== FORMULES DE GESTION DE STOCK ===

1. CMM (Consommation Moyenne Mensuelle)
   CMM = Stock debut - Stock fin

2. SR (Stock de Roulement)
   SR = CMM x (Delai livraison / 30)

3. SS (Stock de Securite)
   SS = 0.5 x CMM x (Delai livraison / 30)

4. SMin (Stock Minimum)
   SMin = SS + (CMM x Delai livraison / 30)

5. SMax (Stock Maximum)
   SMax = SR + SMin

6. QAC (Quantite A Commander)
   QAC = SMax - Stock Disponible"""
    
    def calculer(self, message):
        parts = message.split()
        if len(parts) < 2:
            return "Usage: calculer <nom_produit>"
        
        nom = parts[1]
        data = stock_manager.load_stock()
        
        if nom not in data:
            return f"Produit '{nom}' non trouve. Utilisez 'ajouter' pour l'ajouter."
        
        info = data[nom]
        resultat = stock_manager.analyser_produit(
            nom, info["stock_actuel"], info["cmm"], info["delai_livraison_jours"]
        )
        
        return self.formater_analyse(resultat)
    
    def formater_analyse(self, r):
        return f"""=== Analyse : {r['nom']} ===
Stock actuel : {r['stock_actuel']:.0f}
CMM          : {r['cmm']:.2f}
SR           : {r['sr']:.2f}
SS           : {r['ss']:.2f}
SMin         : {r['smin']:.2f}
SMax         : {r['smax']:.2f}
QAC          : {r['qac']:.2f}
Statut       : {r['statut']}"""
    
    def rechercher_medoc(self, message):
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: rechercher <nom du medicament>"
        
        query = parts[1]
        resultats = bdpm_loader.rechercher_medoc(query)
        
        if not resultats:
            return f"Aucun medicament trouve pour '{query}'."
        
        lignes = [f"=== Resultats pour '{query}' ({len(resultats)} trouve(s)) ===\n"]
        lignes.append(f"{'CIS':<12} {'Nom':<50} {'Forme':<20} {'Statut'}")
        lignes.append("-" * 100)
        
        for r in resultats[:15]:
            nom = r['nom'][:48] if len(r['nom']) > 48 else r['nom']
            forme = r['forme'][:18] if len(r['forme']) > 18 else r['forme']
            lignes.append(f"{r['cis']:<12} {nom:<50} {forme:<20} {r['commercialise']}")
        
        if len(resultats) > 15:
            lignes.append(f"\n... et {len(resultats) - 15} autres resultats")
        
        lignes.append("\nUtilisez 'info <CIS>' pour plus de details")
        return "\n".join(lignes)
    
    def info_medoc(self, message):
        parts = message.split()
        if len(parts) < 2:
            return "Usage: info <CIS>"
        
        cis = parts[1]
        info = bdpm_loader.get_info_cis(cis)
        
        if not info:
            return f"Aucun medicament trouve avec le CIS '{cis}'."
        
        compositions = bdpm_loader.load_compositions()
        comp = compositions.get(cis, [])
        
        symptome_info = symptomes_db.get_symptomes_medoc(info['nom'])
        
        lignes = [f"=== Information : {info['nom']} ===\n"]
        lignes.append(f"CIS             : {info['cis']}")
        lignes.append(f"Forme           : {info['forme']}")
        lignes.append(f"Voie            : {info['voie']}")
        lignes.append(f"Statut          : {info['statut']}")
        lignes.append(f"Procedure       : {info['procedure']}")
        lignes.append(f"Commercialise   : {info['commercialise']}")
        lignes.append(f"Date autorisation: {info['date_autorisation']}")
        lignes.append(f"Titulaire       : {info['titulaire']}")
        lignes.append(f"Generique       : {info['is generique']}")
        
        if comp:
            lignes.append("\n--- Composition ---")
            for c in comp:
                lignes.append(f"  - {c['substance']}: {c['dosage']}")
        
        if symptome_info:
            lignes.append("\n--- Utilisation ---")
            lignes.append(f"Classe          : {symptome_info['classe']}")
            lignes.append(f"Symptomes       : {', '.join(symptome_info['symptomes'])}")
        
        return "\n".join(lignes)
    
    def formater_symptomes(self, resultats, symptome):
        lignes = [f"=== Medicaments pour '{symptome}' ({len(resultats)} trouve(s)) ===\n"]
        lignes.append(f"{'Nom':<20} {'Classe':<35} {'Symptomes'}")
        lignes.append("-" * 90)
        
        for r in resultats:
            symptomes = ', '.join(r['symptomes'][:4])
            lignes.append(f"{r['nom']:<20} {r['classe']:<35} {symptomes}")
        
        return "\n".join(lignes)
    
    def rechercher_symptome(self, message):
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: symptome <mot>"
        
        symptome = parts[1]
        resultats = symptomes_db.rechercher_par_symptome(symptome)
        
        if not resultats:
            return f"Aucun medicament trouve pour le symptome '{symptome}'."
        
        return self.formater_symptomes(resultats, symptome)
    
    def rechercher_pour(self, message):
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: pour <maladie>"
        
        maladie = parts[1]
        resultats = symptomes_db.rechercher_par_symptome(maladie)
        
        if not resultats:
            return f"Aucun medicament trouve pour '{maladie}'."
        
        lignes = [f"=== Medicaments pour traiter '{maladie}' ===\n"]
        
        for r in resultats:
            lignes.append(f"  {r['nom'].upper()}")
            lignes.append(f"  Classe : {r['classe']}")
            lignes.append(f"  Indications : {', '.join(r['symptomes'])}")
            lignes.append("")
        
        return "\n".join(lignes)
    
    def rechercher_rag(self, message):
        parts = message.split(maxsplit=1)
        question = parts[1] if len(parts) > 1 else message
        
        resultats = rag_rechercher(question, k=3, score_min=0.25)
        
        if not resultats:
            resultats = symptomes_db.rechercher_par_symptome(question)
            if resultats:
                return self.formater_symptomes(resultats, question)
            return f"Je n'ai pas trouve de reponse precise pour: {question}\nEssayez 'help' pour voir les commandes disponibles."
        
        lignes = []
        
        meilleur = resultats[0]
        lignes.append(meilleur["texte"])
        
        if len(resultats) > 1:
            lignes.append("\n--- Sources similaires ---")
            for r in resultats[1:]:
                lignes.append(f"  (score: {r['score']:.2f}) {r['texte'][:100]}...")
        
        return "\n".join(lignes)
    
    def lister_classes(self):
        classes = symptomes_db.lister_classes()
        lignes = ["=== Classes Therapeutiques ===\n"]
        for c in classes:
            lignes.append(f"  {c}")
        return "\n".join(lignes)
    
    def lister_symptomes(self):
        symptomes = symptomes_db.lister_symptomes()
        lignes = ["=== Symptomes Recherchables ===\n"]
        for s in symptomes:
            lignes.append(f"  {s}")
        return "\n".join(lignes)
    
    def statistiques(self):
        nb = bdpm_loader.count_medicaments()
        
        return f"""=== Statistiques ===
BDPM Specialites   : {nb}
Base symptomes     : {len(symptomes_db.SYMPTOMES_MEDIAMENTS)} medicaments
Classes            : {len(symptomes_db.lister_classes())}
Symptomes          : {len(symptomes_db.lister_symptomes())}
Index RAG          : Charge
Source BDPM        : base-donnees-publique.medicaments.gouv.fr
Licence            : Etalab-2.0"""
