from pharmacy_bot import PharmacyBot

def main():
    print("=" * 50)
    print("   IA Pharmacie - Assistant de Gestion")
    print("=" * 50)
    print()
    
    bot = PharmacyBot()
    
    print()
    print("Tapez 'help' pour voir les commandes disponibles.")
    print("Tapez 'quit' pour quitter.")
    print()
    
    while True:
        try:
            message = input("Pharmacie> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir !")
            break
        
        if not message:
            continue
        
        reponse, quitter = bot.repondre(message)
        print()
        print(reponse)
        print()
        
        if quitter:
            break

if __name__ == "__main__":
    main()
