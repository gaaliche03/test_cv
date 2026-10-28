# Test technique AI Engineer — API de parsing de CV

## 1. Présentation

Ce projet réalise une API FastAPI de parser de CV pour un cas d'usage RH. Elle reçoit un document, extrait son texte (avec OCR si nécessaire), utilise GPT-5 via Azure OpenAI pour structurer les informations selon un schéma défini, valide la réponse avec Pydantic, puis l'enregistre dans une base des données avec SQLite.

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
Extraction de texte natif
        |
        +-- texte insuffisant / images --> OCR Tesseract
        |
        v
Azure OpenAI — GPT-5
        |
        v
Validation du schéma Pydantic (CVData)
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
│   ├── extraction.py     # Extraction native, sélection et fusion avec l'OCR
│   ├── ocr.py            # OCR Tesseract et conversion LibreOffice
│   ├── llm.py            # Appel à Azure OpenAI et consignes d'extraction
│   ├── schema.py         # Modèles Pydantic et types du JSON
│   └── database.py       # Enregistrement et lecture SQLite
├── data/
│   └── eda.ipynb         # Analyse exploratoire des CV (données locales non incluses)
├── test/                 # Test des codes réalisés
│   ├── test_api.ipynb
│   ├── test_db.ipynb
│   ├── test_extraction.ipynb
│   └── test_llm.ipynb
├── Dockerfile            # Configuration du Docker
├── .dockerignore
├── .gitignore
├── requirements.txt
└── README.md
```

## 3. Choix techniques

### Choix techniques

| Composant | Technologie | Justification |
|---|---|---|
| API | FastAPI | Création des endpoints et documentation Swagger |
| PDF | PyMuPDF | Extraction du texte, des liens et des images |
| Word | python-docx | Extraction du contenu des fichiers DOCX |
| PowerPoint | python-pptx | Extraction du contenu des fichiers PPTX |
| OCR | Tesseract, pytesseract, Pillow | Extraction du texte des images et documents scannés |
| Conversion | LibreOffice | Conversion en PDF si nécessaire pour l'OCR |
| LLM | Azure OpenAI (GPT-5) | Extraction des informations structurées des CV |
| Validation | Pydantic | Vérification de la structure et des types du JSON |
| Stockage | SQLite | Enregistrement des résultats sans serveur externe |
| Déploiement | Docker | Facilite l'installation et l'exécution du projet |
| Qualité du code | Ruff | Vérification du style du code (PEP 8) |

L'approche hybride (extraction native + OCR) permet d'utiliser l'OCR uniquement lorsque c'est nécessaire. Le LLM analyse ensuite le texte extrait pour identifier et organiser les informations du CV dans un JSON structuré.

## 4. Prérequis et configuration

### Option recommandée : Docker

- Docker Desktop (ou Docker Engine) installé et démarré
- Accès réseau au service Azure OpenAI et identifiants Azure valides
- Port `8000` disponible

L'image utilise Python 3.12, et installe Tesseract (anglais et français), LibreOffice et les bibliothèques de `requirements.txt`.

Créer un fichier `.env` à la racine du projet :

```dotenv
BASE_URL=https://VOTRE-ENDPOINT-AZURE
APIM_KEY=VOTRE_CLE_AZURE
API_VERSION=2025-01-01-preview
CHAT_DEPLOYMENT=gpt-5
```

### Versions des dépendances

Les dépendances Python et leurs versions sont précisées dans `requirements.txt`. L'utilisation de Docker permet de reproduire l'environnement d'exécution.

## 5. Installation et lancement avec Docker

**1. Construire l'image Docker** depuis la racine du projet :

```powershell
docker build -t test-cv .
```

**2. Lancer l'application :**

```powershell
docker run --name test-cv-api --env-file .env -p 8000:8000 -v cv_data:/app/data test-cv
```

L'API est accessible via Swagger : http://localhost:8000/docs

Le volume `cv_data` permet de conserver les données SQLite.

**3. Pour les prochains démarrages :**

```powershell
docker start -a test-cv-api
```

Pour arrêter l'application, utiliser `Ctrl+C` ou :

```powershell
docker stop test-cv-api
```

En cas de modification du code, reconstruire l'image avec `docker build -t test-cv .`, puis recréer le conteneur.

## 6. Endpoints et utilisation

### `POST /cvs` — ingestion et parsing

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

Cet exemple illustre la forme et les types, et non un résultat extrait d'un CV réel. Les champs textuels/optionnels absents sont `null`, les listes absentes sont `[]`, et `is_current` est un booléen (`true`/`false`) ou `null`. Les clés non prévues sont refusées (`extra="forbid"`).

### Codes de réponse gérés

| Code| Cas |
|---|---|
|`200`| Traitement ou récupération réussi|
|`400`| Extension de fichier non prise en charge|
|`404`| Nom de fichier absent de la base (GET)|
|`422`| CV invalide / erreur de validation de requête|
|`502`| Échec de l'appel au LLM ou absence de réponse structurée |

## 7. Tests et qualité du code

Les notebooks du dossier `test/` permettent des vérifications manuelles ciblées :

- `test_api.ipynb` : appels à l'API avec `TestClient`, dont un fichier non pris en charge et un CV absent
- `test_db.ipynb` : enregistrement et récupération de données SQLite
- `test_extraction.ipynb` : extraction native et OCR sur des CV de différents formats
- `test_llm.ipynb` : essais d'extraction structurée avec Azure OpenAI

Une analyse exploratoire des formats et de la qualité d'extraction est également disponible dans `data/eda.ipynb`. Les notebooks d'exploration nécessitent les CV de test locaux et peuvent nécessiter des bibliothèques supplémentaires (`pandas`, `matplotlib`, Jupyter) non incluses dans l'image Docker de l'API.

### Vérification PEP 8 avec Ruff

Ruff a été utilisé pour vérifier le respect des bonnes pratiques PEP 8.

ruff format app/

ruff check app/ --select E4,E7,E9,F,I,E501

ruff format test/

ruff check test/ --select E4,E7,E9,F,I,E501

Résultat : All checks passed!

## 8. Limites

- **Formats :** seuls les fichiers PDF, DOCX et PPTX sont acceptés.
- **OCR :** utilisé lorsque l'extraction du texte est insuffisante. La qualité dépend du document.
- **LLM :** l’extraction des informations et les réponses du LLM peuvent contenir des erreurs, malgré la validation Pydantic.
- **Stockage :** les résultats sont enregistrés dans SQLite, sans conserver les fichiers originaux.
- **Tests :** les vérifications sont réalisées avec des notebooks et Ruff, sans suite de tests automatisés complète.
