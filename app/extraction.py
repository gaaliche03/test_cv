# extraction.py : extraire le texte natif des CV
# et utiliser OCR pour les parties non détectées (images)

import logging
from io import BytesIO
from pathlib import Path

import pymupdf
from docx import Document
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from app.ocr import images_utiles, ocr_complet, ocr_images, ocr_page_pdf

logger = logging.getLogger(__name__)


# lire le texte et les liens dans PDF
def lire_pdf(path, langues="eng+fra"):
    textes = []
    liens = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            texte = page.get_text().strip()
            if len(texte) < 100:
                # OCR sur toute la page
                logger.info("OCR page %d", page.number + 1)
                texte_ocr = ocr_page_pdf(page, langues)
            else:
                # OCR des images de la page
                images = []
                for info in page.get_images(full=True):
                    try:
                        image = pdf.extract_image(info[0])["image"]

                        with Image.open(BytesIO(image)) as img:
                            if min(img.size) >= 100 and image not in images:
                                images.append(image)

                    except (RuntimeError, ValueError, KeyError, OSError):
                        continue
                texte_ocr = ocr_images(images, langues)
            textes.append(fusionner_textes(texte, texte_ocr))
            for lien in page.get_links():
                if lien.get("uri"):
                    liens.append(lien["uri"])
    return "\n".join(textes), liens


# lire les paragraphes, tableaux et liens dans Word
def lire_docx(path):
    doc = Document(path)
    textes = []
    liens = []

    # lire le corps du document dans l'ordre
    for element in doc.iter_inner_content():
        if hasattr(element, "rows"):
            for ligne in element.rows:
                textes.append(" | ".join(cell.text.strip() for cell in ligne.cells))
        else:
            if element.text.strip():
                textes.append(element.text.strip())

    # lire les en-têtes et pieds de page
    for section in doc.sections:
        for partie in [section.header, section.footer]:
            for paragraph in partie.paragraphs:
                if paragraph.text.strip():
                    textes.append(paragraph.text.strip())

            for table in partie.tables:
                for ligne in table.rows:
                    textes.append(" | ".join(cell.text.strip() for cell in ligne.cells))

    # récupérer les liens externes
    parties = [doc.part]

    for section in doc.sections:
        parties.extend([section.header.part, section.footer.part])

    for partie in parties:
        for relation in partie.rels.values():
            if relation.reltype.endswith("/hyperlink") and relation.is_external:
                liens.append(relation.target_ref)

    return "\n".join(textes), list(dict.fromkeys(liens))


# lire les zones de texte, tableaux et liens dans PowerPoint
def lire_pptx(path):
    pptx = Presentation(path)
    textes = []
    liens = []

    for slide in pptx.slides:
        formes = list(slide.shapes)

        while formes:
            forme = formes.pop(0)

            # parcourir les formes groupées
            if forme.shape_type == MSO_SHAPE_TYPE.GROUP:
                formes = list(forme.shapes) + formes
                continue

            # lire les tableaux
            if forme.has_table:
                for ligne in forme.table.rows:
                    textes.append(" | ".join(cell.text.strip() for cell in ligne.cells))

            # lire les zones de texte
            if forme.has_text_frame:
                texte = forme.text.strip()

                if texte:
                    textes.append(texte)

                # récupérer les liens dans le texte
                for p in forme.text_frame.paragraphs:
                    for run in p.runs:
                        if run.hyperlink.address:
                            liens.append(run.hyperlink.address)

            # récupérer les liens associés aux formes
            try:
                url = forme.click_action.hyperlink.address
                if url:
                    liens.append(url)
            except (AttributeError, TypeError):
                pass

    return "\n".join(textes), list(dict.fromkeys(liens))


# combiner texte natif et OCR sans répéter le texte identique
def fusionner_textes(natif, ocr):
    natif = natif.strip()
    ocr = ocr.strip()

    if not ocr:
        return natif

    if not natif:
        return ocr

    if ocr in natif:
        return natif

    # conserver les deux textes si différents
    return f"{natif}\n\nComplément OCR :\n{ocr}"


# extraire le texte du CV
def extraire_cv(path, langues="eng+fra"):
    path = Path(path)
    logger.info("début d'extraction du cv")
    if not path.is_file():
        raise FileNotFoundError(f"fichier introuvable : {path}")

    extension = path.suffix.lower()

    if extension not in {".pdf", ".docx", ".pptx"}:
        raise ValueError(f"format non supporté : {extension}")
    logger.debug("format détecté: %s", extension)

    # step1 : extraction native
    if extension == ".pdf":
        texte, liens = lire_pdf(path, langues)

    elif extension == ".docx":
        texte, liens = lire_docx(path)

    else:
        texte, liens = lire_pptx(path)

    # step2 : OCR si nécessaire pour DOCX et PPTX
    if extension in {".docx", ".pptx"}:
        images = images_utiles(path, extension)

        if len(texte.strip()) < 100:
            logger.info("texte natif insuffisant, OCR complet")
            texte_ocr = ocr_complet(path, extension, langues)

        elif images:
            logger.info("OCR des images intégrées")
            texte_ocr = ocr_images(images, langues)

        else:
            texte_ocr = ""

        texte = fusionner_textes(texte, texte_ocr)

    # step3 : ajouter les liens
    liens = list(dict.fromkeys(liens))

    if liens:
        texte += "\n\nLiens présents dans le CV :\n"
        texte += "\n".join(liens)

    texte = texte.replace("\ufeff", "").strip()

    if not texte:
        raise ValueError("aucun texte trouvé dans le CV")
    logger.info("extraction du texte terminée")
    logger.debug("nombre de caractères: %d", len(texte))
    return texte
