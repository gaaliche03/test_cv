# database.py permet de enregistrer json retournés

import sqlite3
from pathlib import Path

from app.schema import CVData

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


def save_cv(filename: str, result: CVData):
    with sqlite3.connect(db) as connexion:
        s = connexion.execute(
            "INSERT INTO cv (filename,data) VALUES (?,?)",
            (filename, result.model_dump_json()),
        )
        return s.lastrowid


# recuperer cv à partir du filename
def lire_cv(filename: str):
    with sqlite3.connect(db) as connexion:
        json = connexion.execute(
            "SELECT data from cv WHERE filename=? ORDER BY id DESC", (filename,)
        ).fetchone()
    if json is None:
        return None
    return CVData.model_validate_json(json[0])
