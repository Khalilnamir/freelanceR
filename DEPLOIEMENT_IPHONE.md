# Déployer Freelance Radar AI sur Streamlit Community Cloud depuis un iPhone

## 0. Ce qui fonctionne / ne fonctionne pas encore

- L'interface Streamlit, la collecte manuelle de flux RSS, le scoring, la gestion de signaux et la préparation de brouillons fonctionnent sans ordinateur.
- Pas de collecte continue ni d'envoi automatique d'emails : un orchestrateur externe sera ajouté ultérieurement.
- La base SQLite locale **peut disparaître** lorsque Streamlit redémarre ou redéploie. Une fonction de sauvegarde/restauration JSON est disponible dans l'application. Pour un CRM durable, intégrer une vraie base cloud (Supabase, par exemple).

## 1. Créer un dépôt GitHub **privé**

1. Sur iPhone, ouvre https://github.com/new et connecte-toi.
2. Nom : `freelance-radar-ai` ; visibilité : **Private**.
3. Crée le dépôt sans fichier d'exemple (ou avec, les deux fonctionnent).
4. Dans l'app Fichiers de l'iPhone, décompresse ce ZIP ; dans GitHub, choisis `Add file` > `Upload files` et importe les fichiers du projet. Si l'interface mobile ne montre pas cette option, active **Version pour ordinateur** dans Safari.
5. Vérifie que ces fichiers sont bien à la racine du dépôt : `app.py`, `radar.py`, `profile.json`, `requirements.txt` (le reste peut aussi être importé).
6. Ne mets jamais le CV original, la base SQLite, une adresse email de prospect ou des secrets dans ce dépôt.

## 2. Connecter Streamlit

1. Va sur https://share.streamlit.io/ et connecte-toi avec GitHub.
2. Autorise l'accès à ton dépôt privé si Streamlit le demande.
3. `Create app` > `Yup, I have an app`.
4. Sélectionne ton dépôt `freelance-radar-ai`, branche `main`, fichier `app.py`.
5. Avant de cliquer sur `Deploy`, ouvre `Advanced settings` > `Secrets` et colle **avec une valeur de ton choix** :

   ```toml
   APP_PASSWORD = "REMPLACE_PAR_UN_MOT_DE_PASSE_LONG_ET_UNIQUE"
   ```

   Choisis une vraie phrase de passe d'au moins 12 caractères. Ne laisse surtout pas le texte d'exemple.
6. Lance `Deploy`.
7. Dans les paramètres de partage, garde l'application **privée**.

## 3. Depuis ton iPhone

- Ouvre l'URL `*.streamlit.app` fournie par Streamlit.
- Connecte-toi avec la phrase de passe choisie.
- Onglet `🔎 Scanner` : lance un premier scan.
- Onglet `🎯 Opportunités` : vérifie les sources et les hypothèses de besoin.
- Onglet `💾 Sauvegarde` : exporte les pistes régulièrement, puis restaure-les si le serveur redémarre.
- Safari > Partager > `Sur l'écran d'accueil` pour avoir un raccourci.

## Prochaines étapes techniques

1. Base Postgres persistante avec contrôle d'accès pour les signaux et le CRM.
2. Traitement automatique des flux via n8n Cloud ou un job planifié séparé.
3. Enrichissement IA des signaux à partir de sources autorisées et vérifiables.
4. Contacts professionnels sourcés et prospection B2B avec consentements/oppositions gérés correctement.

Références :
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app
- https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
