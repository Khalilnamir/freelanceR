"""Point d'entrée pour un scan déclenché par un planificateur externe."""
from radar import scan

if __name__ == "__main__":
    result = scan()
    print(f"Scan UTC {result['run_at']} : {result['found']} vus, {result['added']} nouveaux, {len(result['errors'])} erreurs")
    for error in result["errors"]:
        print("ERREUR:", error)
