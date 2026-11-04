# database.py : enregistrer les JSON retournés par le LLM

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)
db = Path(__file__).resolve().parent.parent / "data" / "cvs.db"

def connexion_db():
    db.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db) as connexion:
        connexion.execute(
            """CREATE TABLE IF NOT EXISTS cv (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            data TEXT NOT NULL)"""
        )
    logger.info("Base de données initialisée")


def save_cv(filename: str, result: dict):
    with sqlite3.connect(db) as connexion:
        s = connexion.execute(
            "INSERT INTO cv (filename, data) VALUES (?, ?)",
            (filename, json.dumps(result, ensure_ascii=False)),
        )
    logger.info("CV enregistré dans SQLite")
    return s.lastrowid


# récupérer le CV à partir du filename
def lire_cv(filename: str):
    with sqlite3.connect(db) as connexion:
        resultat = connexion.execute(
            "SELECT data FROM cv WHERE filename=? ORDER BY id DESC", (filename,)
        ).fetchone()

    if resultat is None:
        logger.warning("CV non trouvé dans SQLite")
        return None

    logger.info("CV récupéré depuis SQLite")
    return json.loads(resultat[0])
