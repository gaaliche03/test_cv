import os

import openai
from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schema import CVData

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
8. Pour les dates, utilise YYYY-MM si le mois est connu,
YYYY si seule l'année est connue, et present pour un poste en cours.
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
        return None
    try:
        reponse = client.beta.chat.completions.parse(
            model=os.getenv("CHAT_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": texte},
            ],
            response_format=CVData,
            max_completion_tokens=4000,
            reasoning_effort="minimal",
        )
        resultat = reponse.choices[0].message
        if resultat.parsed is None:
            print("aucune donnée structurée retournée:", resultat.refusal)
            return None
        return resultat.parsed
    except openai.OpenAIError as erreur:
        print("erreur Azure OpenAI:", erreur)
        return None
