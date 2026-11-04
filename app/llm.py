import json
import logging
import os

import openai
from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schema import CVData

logger = logging.getLogger(__name__)

load_dotenv()
client = AzureOpenAI(
    api_version=os.getenv("API_VERSION"),
    azure_endpoint=os.getenv("BASE_URL"),
    api_key="placeholder",
    default_headers={"Ocp-Apim-Subscription-Key": os.getenv("APIM_KEY")},
    max_retries=0,
    timeout=60,
)

prompt = """ Tu es un assistant chargé d'extraire les informations d'un CV.
Le texte provient d'un PDF, Word ou PowerPoint et peut contenir
des erreurs OCR, des colonnes mélangées ou des caractères mal reconnus.
Règles :
1. Utilise uniquement les informations présentes dans le CV.
N'invente aucune information.
2. Respecte exactement le schéma JSON demandé.
Tous les champs du schéma doivent être présents.
N'ajoute aucun champ supplémentaire et ne force pas les informations
hors schéma dans une catégorie inadaptée.
3. Si une information est absente,
utilise null pour les champs textuels ou booléens,
et une liste vide pour les listes.
4. Sépare correctement le prénom et le nom du candidat.
5. Conserve les coordonnées et les liens de profil du candidat. 
Pour LinkedIn et GitHub, accepte uniquement les URL pointant
vers un profil personnel identifiable.
Ignore les liens génériques vers les pages d'accueil des plateformes.
Si aucun lien de profil valide n'est présent, utilise null.
N'invente jamais d'URL.
6. Identifie les compétences techniques, les compétences humaines
et les langues lorsqu'elles sont mentionnées.
7. Extrais toutes les expériences professionnelles,
stages inclus, ainsi que les formations.
8. Pour les dates :
- Utiliser YYYY-MM si le mois et l'année sont connus.
- Utiliser YYYY si seule l'année est connue.
- Utiliser null si la date est absente.
- Pour une expérience en cours, end_date = null.
- Ne jamais inventer de dates.
9. Pour le champ city, retourne uniquement le nom de la ville,
sans adresse ni code postal.
10. Dans le champ soft_skills, conserve uniquement les compétences
comportementales et interpersonnelles.
Ne classe pas les domaines métier comme des soft skills.
11. Conserve les descriptions des expériences dans la langue du CV.
12. Corrige les erreurs OCR évidentes, notamment dans les noms
des technologies, frameworks et langages de programmation.
Utilise leur orthographe officielle lorsque le contexte
permet de les identifier avec confiance.
Si un terme est ambigu, conserve le texte original.
13. Pour chaque expérience professionnelle, remplis le champ
technologies avec les technologies explicitement mentionnées
dans la description de cette expérience.
Ne copie pas les compétences de la section générale SKILLS.
Si aucune technologie n'est mentionnée dans cette expérience,
utilise une liste vide."""


def extraire_informations(texte):
    if not texte.strip():
        logger.warning("texte vide envoyé au LLM")
        return None
    logger.info("début appel GPT-5")
    try:
        reponse = client.chat.completions.create(
            model=os.getenv("CHAT_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": texte},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "cv_extraction",
                    "strict": True,
                    "schema": CVData,
                },
            },
            max_completion_tokens=4000,
            reasoning_effort="minimal",
        )
        choix = reponse.choices[0]
        resultat = choix.message

        if resultat.refusal or choix.finish_reason != "stop":
            logger.warning(
                "réponse LLM refusée ou incomplète : %s", choix.finish_reason
            )
            return None

        if not resultat.content:
            logger.warning("Réponse LLM vide")
            return None
        logger.info("Extraction JSON réussie")
        return json.loads(resultat.content)

    except (openai.OpenAIError, json.JSONDecodeError):
        logger.exception("Erreur pendant l'extraction LLM")
        return None
