# 📡 Freelance Radar AI · MVP 0.2 Cloud

Un prototype Streamlit compatible Community Cloud, adapté au CV fourni, pour détecter des **signaux off-market** Data / IA et préparer une prospection B2B ciblée.

## Fonctionnalités réellement disponibles

- Scanner plusieurs requêtes via des flux RSS publics de Google News (internet requis).
- Importer manuellement une information publique avec son URL.
- Dédupliquer par URL et historiser dans SQLite.
- Scorer les signaux avec des règles **heuristiques expliquées** (pas de fausse probabilité de mission).
- Filtrer, qualifier les entreprises, enregistrer les contacts professionnels et leurs sources.
- Conserver une opposition « ne plus contacter ».
- Générer un **brouillon** personnalisé à partir de ton expérience réelle, sans inventer de faits.
- Exporter les pistes en CSV.
- Déclencher un scan en ligne de commande pour une planification externe.

### Ce qui n'est PAS encore automatisé

- Identification et vérification automatiques des interlocuteurs ou de leurs emails.
- Analyse des articles complets ni vérification indépendante des informations relayées dans les RSS.
- Détection de postes LinkedIn avec navigateur ou envoi de messages LinkedIn.
- Envoi d'emails, de CV ou candidatures, traitement des réponses, relances.
- Scraping de sites qui l'interdisent ; aucune connexion à des comptes personnels.

## Déploiement sur Streamlit Community Cloud depuis iPhone

**Lis `DEPLOIEMENT_IPHONE.md`** : ce guide explique comment mettre les fichiers dans un dépôt GitHub privé, configurer le secret `APP_PASSWORD` dans Streamlit Community Cloud et lancer l'application.

Important : ne publie pas de données prospects dans un dépôt GitHub ; la sauvegarde manuelle JSON contient potentiellement des données confidentielles. La base SQLite hébergée n'est **pas persistante** et ne doit pas être considérée comme un CRM durable.

## Démarrage en local (Python 3.10+)

**Windows PowerShell**

```powershell
cd freelance-radar-ai
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

**macOS/Linux**

```bash
cd freelance-radar-ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

L'interface apparaît à `http://localhost:8501`. Au premier lancement, le tableau de bord est vide : **aucun résultat fictif n'est présenté comme réel**. Ouvre « Scanner des sources », puis lance un scan. Selon la disponibilité des flux et leur couverture, les résultats peuvent être peu nombreux ou imprécis.

## Automatiser la collecte (pas les emails)

Sur un serveur ou un ordinateur allumé, planifier :

```bash
python scan.py
```

Cela collecte les RSS et ajoute les nouveaux signaux ; **cela ne contacte personne**. Exemple de planification (Linux cron) : `0 8,13,18 * * 1-5` pour exécuter la commande aux heures configurées par le serveur, depuis le répertoire du projet avec le bon environnement Python.

## Configuration

- `APP_PASSWORD` : secret Streamlit **obligatoire** (12 caractères minimum). En local, crée `.streamlit/secrets.toml` avec le même champ ; ne commite jamais ce fichier.
- Onglet Sauvegarde : téléchargement et réimport de signaux en JSON, sans écraser les lignes déjà présentes.

- `profile.json` : ton CV transformé en profil commercial structuré ; **aucune coordonnée personnelle incluse**.
- `radar.py` : mots-clés, types de signaux, moteurs RSS et scoring.
- `app.py` : tableau de bord et suivi.
- `radar.sqlite3` : base générée localement au premier lancement. Ne pas publier cette base.

Le TJM 680 €/jour sert seulement de **référence de départ à confirmer**, pas de prix public ni de filtre de revenu dans ce MVP.

## Interprétation des signaux

Les résultats RSS ne confirment **ni budget disponible, ni volonté de recourir à un freelance**. Il faut : 1) consulter la source, 2) identifier l'entreprise correcte, 3) vérifier l'hypothèse de besoin, 4) trouver un contact pertinent sur des sources professionnelles autorisées, 5) vérifier les obligations de prospection avant tout envoi.

## Sécurité, RGPD et conditions des plateformes

- Aucun mot de passe LinkedIn n'est demandé et aucune interaction LinkedIn n'est automatisée.
- Ne pas copier d'informations privées ou sensibles à propos d'employés. Ne traiter que des annonces professionnelles publiques pertinentes.
- Pour une future phase d'outreach email : respecter les conditions de la prospection B2B, provenance des données, information, opposition, limitation d'envois, conservation et suppression, traitement des demandes « stop », et privilégier les adresses professionnelles.
- Ne pas committer de secrets, ni de base d'email de prospects. Vérifier les permissions et licences des sources avant d'industrialiser la collecte.
- L'envoi autonome exige un branchement à un service email autorisé et un contrôle de conformité, **non inclus** dans cette version.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Roadmap réaliste

1. **MVP 0.2 Cloud (ce livrable)** : profil depuis le CV, veille RSS, scoring, journal, brouillons.
2. **MVP 0.2** : extraction structurée des entreprises avec LLM, recoupement et fiabilité des sources, API BOAMP, connecteurs ATS autorisés, alertes email.
3. **MVP 0.3** : recherche/validation des contacts via prestataire B2B autorisé + suivi des sources et des oppositions.
4. **MVP 0.4** : envoi email authentifié sous contrôle de règles, quotas et désinscription, analyse des réponses, CRM et relances.
5. **MVP 1.0** : hébergement planifié, monitoring, mesure du taux de réponse et des entretiens.

Sources de référence : https://www.boamp.fr/pages/donnees-ouvertes-et-api/ ; https://www.linkedin.com/legal/user-agreement ; https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique
