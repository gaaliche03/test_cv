# ocr.py: reconnaissance du texte présent dans les images grâce à Tesseract
import hashlib
import logging
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
import pytesseract
from docx import Document
from PIL import Image, ImageOps
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

logger = logging.getLogger(__name__)


# préparer une image et extraire son texte avec tesseract
def ocr_image(image, langues="eng+fra"):
    # ajouter un fond blanc aux images transparentes
    rgba = image.convert("RGBA")
    fond = Image.new("RGBA", rgba.size, "white")
    image = Image.alpha_composite(fond, rgba)

    # convertir en niveaux de gris
    image = ImageOps.grayscale(image.convert("RGB"))

    # agrandir pour faciliter la reconnaissance
    image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)

    return pytesseract.image_to_string(image, lang=langues).strip()


# convertir une page pdf en image puis appliquer ocr
def ocr_page_pdf(page, langues="eng+fra"):
    pix = page.get_pixmap(dpi=200, colorspace=pymupdf.csRGB, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return ocr_image(image, langues)


taille_min = 100


# récupérer les images intégrées dans tous les formats
def images_utiles(path, extension):
    blobs = []
    if extension == ".pdf":
        with pymupdf.open(path) as pdf:
            for page in pdf:
                for info in page.get_images(full=True):
                    try:
                        image = pdf.extract_image(info[0])
                        blobs.append(image["image"])
                    except (RuntimeError, ValueError, KeyError):
                        continue

    elif extension == ".docx":
        doc = Document(path)
        parties = [doc.part]
        for section in doc.sections:
            parties.extend([section.header.part, section.footer.part])
        for partie in parties:
            for relation in partie.rels.values():
                if relation.reltype.endswith("/image"):
                    blobs.append(relation.target_part.blob)

    elif extension == ".pptx":
        pptx = Presentation(path)
        for slide in pptx.slides:
            formes = list(slide.shapes)
            while formes:
                forme = formes.pop(0)
                if forme.shape_type == MSO_SHAPE_TYPE.GROUP:
                    formes = list(forme.shapes) + formes
                elif forme.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    blobs.append(forme.image.blob)

    # supprimer les doublons et les images trop petites
    utiles = []
    vues = set()
    for blob in blobs:
        empreinte = hashlib.sha256(blob).hexdigest()
        if empreinte in vues:
            continue
        vues.add(empreinte)
        try:
            with Image.open(BytesIO(blob)) as image:
                if min(image.size) >= taille_min:
                    utiles.append(blob)
        except (OSError, ValueError):
            continue
    return utiles


# appliquer ocr aux images récupérées
def ocr_images(blobs, langues="eng+fra"):
    textes = []
    for blob in blobs:
        try:
            with Image.open(BytesIO(blob)) as image:
                texte = ocr_image(image, langues)
            if texte:
                textes.append(texte)
        except (OSError, ValueError):
            continue
    return "\n".join(textes)


# appliquer ocr sur les pages du pdf
def ocr_pdf(path, langues="eng+fra"):
    textes = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            texte = ocr_page_pdf(page, langues)
            if texte:
                textes.append(texte)
    return "\n".join(textes)


# ocr complet poour cv contient peu de texte natif
def ocr_complet(path, extension, langues="eng+fra"):
    path = Path(path).resolve()
    if extension == ".pdf":
        return ocr_pdf(path, langues)

    # convertir docx et pptx en pdf avec libreoffice
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        logger.info("Conversion du document en PDF pour OCR")
        with TemporaryDirectory() as dossier:
            try:
                subprocess.run(
                    [
                        soffice,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        dossier,
                        str(path),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
                pdf = Path(dossier) / f"{path.stem}.pdf"
                if pdf.exists():
                    texte = ocr_pdf(pdf, langues)
                    if texte:
                        return texte
            except (subprocess.SubprocessError, OSError):
                logger.warning("Conversion LibreOffice échouée, OCR des images")

    # si libreoffice echoue, use ocr sur images recuperées
    blobs = images_utiles(path, extension)
    return ocr_images(blobs, langues)
