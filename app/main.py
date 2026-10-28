from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.database import connexion_db, lire_cv, save_cv
from app.extraction import extraire_cv
from app.llm import extraire_informations
from app.schema import CVData

app = FastAPI(title="API extraction cv")
connexion_db()


# envoyer cv et récupérer son JSON structuré
@app.post("/cvs", response_model=CVData)
def ajout_cv(file: Annotated[UploadFile, File()]):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    if extension not in [".pdf", ".docx", ".pptx"]:
        raise HTTPException(status_code=400, detail="format non supporté")

    # sauvegarder temporairement file envoyé
    with TemporaryDirectory() as dossier:
        path = Path(dossier) / filename
        path.write_bytes(file.file.read())
        # extraction text
        try:
            texte = extraire_cv(path)
        except ValueError:
            raise HTTPException(status_code=422, detail="cv invalide")

    # appel llm pour obtenir json structuré
    resultat = extraire_informations(texte)
    if resultat is None:
        raise HTTPException(status_code=502, detail="échec d'appel llm")
    save_cv(filename, resultat)
    return resultat


@app.get("/cvs/{filename}", response_model=CVData)
def recupere_cv(filename: str):
    resultat = lire_cv(filename)
    if resultat is None:
        raise HTTPException(status_code=404, detail="cv introuvable")
    return resultat
