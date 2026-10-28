# extraction.py : permet de extraire texte natif des cv
# et utiliser ocr pour cv qui contient des parties non détectées (images)
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from docx import Document
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from app.ocr import images_utiles, ocr_complet, ocr_images, ocr_page_pdf

w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# gerer cas d'ouverture file crée avec un old version par new version
fallback = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


@dataclass  # regrouper infos dans un seul objet
class ResultatCV:
    texte: str
    categorie: str
    caracteres_natifs: int
    nb_images: int
    caracteres_ocr: int


def lire_pdf(path):
    textes = []
    liens = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            textes.append(page.get_text())
            for lien in page.get_links():
                if lien.get("uri"):
                    liens.append(lien["uri"])
    return "\n".join(textes), liens


# lire les pragraphs,tableaux et zone de texte dans word
def paragraphes_word(racine):
    lignes = []
    for paragraph in racine.iter(f"{w}p"):
        if any(p.tag == fallback for p in paragraph.iterancestors()):
            continue
        morceaux = []
        for element in paragraph.iter(f"{w}t", f"{w}br"):
            p = next(element.iterancestors(f"{w}p"), None)

            if p is not paragraph:
                continue
            if element.tag == f"{w}t":
                morceaux.append(element.text or "")
            else:
                morceaux.append("\n")

        ligne = "".join(morceaux).strip()
        if ligne:
            lignes.append(ligne)
    return lignes


def lire_docx(path):
    doc = Document(path)
    entetes = []
    pieds = []
    liens = []
    for section in doc.sections:
        entetes.extend(paragraphes_word(section.header._element))
        pieds.extend(paragraphes_word(section.footer._element))
    corps = paragraphes_word(doc.element.body)
    # .fromkeys permet de supprimer les doublons
    lignes = list(dict.fromkeys(entetes)) + corps + list(dict.fromkeys(pieds))
    parties = [doc.part]

    for section in doc.sections:
        parties.extend([section.header.part, section.footer.part])

    # trouver les links externes
    for partie in parties:
        for relation in partie.rels.values():
            if relation.reltype.endswith("/hyperlink") and relation.is_external:
                liens.append(relation.target_ref)
    return "\n".join(lignes), liens


def lire_pptx(path):
    pptx = Presentation(path)
    textes = []
    liens = []
    for slide in pptx.slides:
        formes = list(slide.shapes)
        while formes:
            forme = formes.pop(0)
            # si forme est un prg, faut ajouter ses elements à parcourir
            if forme.shape_type == MSO_SHAPE_TYPE.GROUP:
                formes = list(forme.shapes) + formes
                continue
            # extraction de texte dans tables
            if forme.has_table:
                for ligne in forme.table.rows:
                    textes.append(" | ".join(cell.text.strip() for cell in ligne.cells))
            # extraction de texte dans les zones de texte
            elif forme.has_text_frame:
                texte = forme.text.strip()
                if texte:
                    textes.append(texte)
                # recuperer liens dans textes
                for p in forme.text_frame.paragraphs:
                    for run in p.runs:
                        if run.hyperlink.address:
                            liens.append(run.hyperlink.address)

            # recuperer les liens associés aux formes
            try:
                url = forme.click_action.hyperlink.address
                if url:
                    liens.append(url)
            except (AttributeError, TypeError):
                pass
    return "\n".join(textes), liens


# combiner extraction classique est ocr sans répéter le texte identique
def fusionner_textes(natif, ocr):
    natif = natif.strip()
    ocr = ocr.strip()
    if not ocr:
        return natif
    if not natif:
        return ocr
    if ocr in natif:
        return natif

    # si les textes sont différents donc conserver les 2
    return f"{natif}\n\ncomplément OCR :\n{ocr}"


seuil_caracteres = 500
seuil_page = 100
formats = {".pdf": lire_pdf, ".docx": lire_docx, ".pptx": lire_pptx}


# extraire le cv et retourner les infos
def analyse_cv(path, seuil=seuil_caracteres, langues="eng+fra"):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"fichier introuvable: {path}")
    extension = path.suffix.lower()
    if extension not in formats:
        raise ValueError(f"format non supporté: {extension}")

    # step1: extraction native
    texte_natif, liens = formats[extension](path)
    texte_natif = texte_natif.strip()
    natifs = len(texte_natif)
    blobs = images_utiles(path, extension)
    nb_images = len(blobs)

    texte_ocr = ""
    categorie = "texte"
    # step2. réaliser ocr si c'est nécessaire

    if extension == ".pdf":
        textes = []
        pages_ocr = 0
        with pymupdf.open(path) as pdf:
            for page in pdf:
                natif_page = page.get_text().strip()
                if len(natif_page) < seuil_page:
                    ocr_page = ocr_page_pdf(page, langues)
                    pages_ocr += 1
                    if ocr_page:
                        texte_ocr += "\n" + ocr_page
                    textes.append(fusionner_textes(natif_page, ocr_page))
                else:
                    textes.append(natif_page)

        texte = "\n".join(textes)
        if pages_ocr:
            categorie = "ocr_pages"
        elif nb_images:
            categorie = "mixte"
            texte_ocr = ocr_images(blobs, langues)
            texte = fusionner_textes(texte, texte_ocr)
    # si il y a peu de texte, essayer ocr sur tout le cv
    elif natifs < seuil:
        categorie = "ocr_complet"
        texte_ocr = ocr_complet(path, extension, langues)
        texte = fusionner_textes(texte_natif, texte_ocr)

    elif nb_images:
        categorie = "mixte"
        texte_ocr = ocr_images(blobs, langues)
        texte = fusionner_textes(texte_natif, texte_ocr)

    else:
        texte = texte_natif

    # step3 ajouter les liens
    liens = list(dict.fromkeys(liens))

    if liens:
        texte += "\n\n liens présents dans cv:\n"
        texte += "\n".join(liens)

    texte = texte.replace("\ufeff", "").strip()

    if not texte:
        raise ValueError("aucun texte trouvé dans cv")
    result = ResultatCV(
        texte=texte,
        categorie=categorie,
        caracteres_natifs=natifs,
        nb_images=nb_images,
        caracteres_ocr=len(texte_ocr.strip()),
    )

    return result


# return que texte dans cv
def extraire_cv(path, seuil=seuil_caracteres, langues="eng+fra"):
    return analyse_cv(path, seuil, langues).texte
