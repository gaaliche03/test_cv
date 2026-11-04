# API de parsing de CV

## 1. Présentation

Ce projet réalise une API FastAPI de parsing de CV pour un cas d'usage RH. Elle reçoit un document, extrait son texte et ses liens (avec OCR si nécessaire), utilise GPT-5 via Azure OpenAI pour structurer les informations selon un schéma JSON défini, puis enregistre le résultat dans une base de données SQLite.

L'objectif est de proposer une solution simple, lisible et reproductible, adaptée à des CV de présentations différentes.

**Formats acceptés par l'API :** `.pdf`, `.docx` et `.pptx`.

## 2. Architecture

```text
CV (PDF / DOCX / PPTX)
        |
        v
FastAPI — POST /cvs
        |
        v
Extraction du texte natif
        |
        +-- texte insuffisant / images --> OCR Tesseract
        |
        v
Fusion du texte natif et du texte OCR
        |
        v
Azure OpenAI — GPT-5
        |
        v
Réponse structurée selon JSON Schema strict (CVData)
        |
        v
SQLite — data/cvs.db
        |
        v
Réponse JSON structurée

FastAPI — GET /cvs/{filename} --> SQLite --> JSON
```

### Organisation du code

```text
test_technique/
├── app/
│   ├── main.py           # API FastAPI : POST et GET
│   ├── extraction.py     # Extraction native et fusion avec l'OCR
│   ├── ocr.py            # OCR Tesseract et conversion LibreOffice
│   ├── llm.py            # Appel à Azure OpenAI et consignes d'extraction
│   ├── schema.py         # Schéma JSON des informations du CV
│   └── database.py       # Enregistrement et lecture SQLite
├── data/
│   └── eda.ipynb         # Analyse exploratoire des CV
├── test/                 # Notebooks de test
│   ├── test_api.ipynb
│   ├── test_db.ipynb
│   ├── test_extraction.ipynb
│   └── test_llm.ipynb
├── Dockerfile            # Configuration Docker
├── .dockerignore
├── .gitignore
├── .env.example          # Exemple de configuration Azure
├── requirements.txt
└── README.md
```

## 3. Choix techniques

| Composant       | Technologie                    | Justification                                         |
| --------------- | ------------------------------ | ----------------------------------------------------- |
| API             | FastAPI                        | Création des endpoints et documentation Swagger       |
| PDF             | PyMuPDF                        | Extraction du texte, des liens et des images          |
| Word            | python-docx                    | Extraction du contenu des fichiers DOCX               |
| PowerPoint      | python-pptx                    | Extraction du contenu des fichiers PPTX               |
| OCR             | Tesseract, pytesseract, Pillow | Extraction du texte des images et documents scannés   |
| Conversion      | LibreOffice                    | Conversion en PDF si nécessaire pour l'OCR            |
| LLM             | Azure OpenAI (GPT-5)           | Extraction des informations structurées des CV        |
| Schéma JSON     | JSON                           | Définition de la structure et des types de la réponse |
| Stockage        | SQLite                         | Enregistrement des résultats sans serveur externe     |
| Déploiement     | Docker                         | Facilite l'installation et l'exécution du projet      |
| Logs            | logging (Python)               | Suivi des étapes du traitement et des erreurs         |
| Qualité du code | Ruff                           | Vérification du style du code (PEP 8)                 |

L'approche hybride (extraction native + OCR) permet d'utiliser l'OCR lorsque le texte est insuffisant ou lorsque des images contiennent du texte. Le LLM analyse ensuite le texte extrait pour identifier et organiser les informations du CV dans un JSON structuré.

## 4. Prérequis et configuration

### Option recommandée : Docker

- Docker Desktop (ou Docker Engine) installé et démarré
- Accès réseau au service Azure OpenAI et identifiants valides
- Port `8000` disponible

L'image utilise Python 3.12 et installe Tesseract (anglais et français), LibreOffice et les bibliothèques de `requirements.txt`.

Copier le fichier `.env.example` en `.env`, puis remplacer les valeurs d'exemple par les paramètres Azure nécessaires (`API_VERSION`, `BASE_URL`, `APIM_KEY` et `CHAT_DEPLOYMENT`). Ne pas publier le fichier `.env`.

### Versions des dépendances

Les dépendances Python sont précisées dans `requirements.txt`. Docker permet de préparer le même environnement d'exécution sur différentes machines.

## 5. Installation et lancement avec Docker

**1. Construire l'image Docker** depuis la racine du projet :

```powershell
docker build -t cv-parse:latest .
```

**2. Lancer l'application :**

```powershell
docker run --name cv-api --env-file .env -p 8000:8000 -v cv_data:/app/data cv-parse:latest
```

L'API est accessible via Swagger : http://localhost:8000/docs

Le volume `cv_data` permet de conserver les données SQLite même si le conteneur est supprimé.

**3. Pour les prochains démarrages :**

```powershell
docker start -a cv-api
```

Pour arrêter l'application, utiliser `Ctrl+C` ou :

```powershell
docker stop cv-api
```

En cas de modification du code, reconstruire l'image puis recréer le conteneur :

```powershell
docker build -t cv-parse:latest .
docker stop cv-api
docker rm cv-api
docker run --name cv-api --env-file .env -p 8000:8000 -v cv_data:/app/data cv-parse:latest
```

## 6. Endpoints et utilisation

### `POST /cvs` — envoi et parsing

Reçoit un fichier dans le champ multipart `file`, extrait les informations, les sauvegarde dans SQLite et renvoie le JSON structuré.

Dans Swagger (`http://localhost:8000/docs`) : ouvrir **POST /cvs**, cliquer sur **Try it out**, sélectionner un CV puis **Execute**.

### `GET /cvs/{filename}` — récupération

Récupère la **dernière version enregistrée** pour le nom de fichier demandé.

### Structure de la réponse JSON

Le schéma est défini dans `app/schema.py` :

```json
{
  "personal_information": {
    "first_name": "Prénom",
    "last_name": "Nom",
    "email": null,
    "phone": null,
    "city": null,
    "linkedin": null,
    "github": null
  },
  "professional_summary": null,
  "skills": {
    "technical_skills": [],
    "soft_skills": [],
    "languages": []
  },
  "work_experience": [
    {
      "job_title": null,
      "company": null,
      "description": null,
      "technologies": [],
      "location": null,
      "start_date": null,
      "end_date": null
    }
  ],
  "education": [
    {
      "degree": null,
      "school_name": null,
      "start_date": null,
      "is_current": null
    }
  ]
}
```

Cet exemple illustre la structure attendue, et non un résultat extrait d'un CV réel. Les champs textuels absents sont `null`, les listes sans éléments sont `[]`, et `is_current` est un booléen (`true`/`false`) ou `null`. Le schéma utilise `additionalProperties: false` pour interdire les champs supplémentaires. Le code utilise la sortie structurée de l'API Azure OpenAI et décode ensuite le JSON retourné.

## 7. Tests et qualité du code

Les notebooks du dossier `test/` permettent des vérifications manuelles ciblées :

- `test_api.ipynb` : appels à l'API avec `TestClient`, dont un fichier non pris en charge et un CV absent
- `test_db.ipynb` : enregistrement et récupération de données SQLite
- `test_extraction.ipynb` : extraction native et OCR sur des CV de différents formats
- `test_llm.ipynb` : essais d'extraction structurée avec Azure OpenAI

Une analyse exploratoire est également disponible dans `data/eda.ipynb`. Les notebooks nécessitent les CV de test locaux et peuvent demander des bibliothèques supplémentaires (`pandas`, `matplotlib`, Jupyter) non incluses dans l'image Docker de l'API.

### Suivi des traitements avec les logs

Le module `logging` de Python est utilisé pour suivre les étapes de traitement des CV : réception du fichier, extraction du texte, utilisation de l’OCR, appel au LLM et enregistrement dans SQLite. Les logs permettent aussi de repérer les erreurs sans modifier le fonctionnement de l’API.

Pour consulter les logs du conteneur Docker :

```powershell
docker logs cv-api
```

Pour les suivre en direct :

```powershell
docker logs -f cv-api
```

### Vérification PEP 8 avec Ruff

Ruff est utilisé pour vérifier le style du code :

```powershell
ruff format app/
ruff check app/ --select E4,E7,E9,F,I,E501

ruff format test/
ruff check test/ --select E4,E7,E9,F,I,E501
```

La vérification est réussie lorsque Ruff affiche `All checks passed!`.

## 8. Limites

- **Formats :** seuls les fichiers PDF, DOCX et PPTX sont acceptés.
- **OCR :** la qualité dépend de la lisibilité des images et des documents scannés.
- **LLM :** les informations extraites peuvent contenir des erreurs, même avec un schéma JSON strict.
- **Stockage :** les résultats sont enregistrés dans SQLite, sans conserver les fichiers originaux.
- **Tests :** les vérifications reposent principalement sur des notebooks et Ruff, sans suite complète de tests automatisés.
