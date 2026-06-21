"""Generate synthetic CV PDFs (1-column and 2-column) for extraction tests.

These reproduce the multi-column layout that breaks reading order: a narrow
left sidebar (contact / langues / competences) next to a wider main column
(name / profil / experiences). Used by test_cv_column_extraction.py.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4  # ~595 x 842 pt


def _para(c, x, y, lines, leading=14, font="Helvetica", size=10):
    """Draw a paragraph block at (x, y). Returns the y after the block."""
    c.setFont(font, size)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def make_two_column_cv(path):
    c = canvas.Canvas(path, pagesize=A4)

    # Geometry: left sidebar ~35% width, main column on the right.
    left_x = 40
    right_x = 250
    top = PAGE_H - 60

    # --- Left sidebar: distinct paragraph blocks separated by vertical gaps ---
    y = top
    y = _para(c, left_x, y, ["CONTACT"], font="Helvetica-Bold", size=11)
    y -= 8
    y = _para(c, left_x, y, ["raphael.martin@email.com", "+33 6 12 34 56 78", "Paris, France"])
    y -= 24
    y = _para(c, left_x, y, ["LANGUES"], font="Helvetica-Bold", size=11)
    y -= 8
    y = _para(c, left_x, y, ["Francais - natif", "Anglais - courant", "Espagnol - courant"])
    y -= 24
    y = _para(c, left_x, y, ["COMPETENCES"], font="Helvetica-Bold", size=11)
    y -= 8
    y = _para(c, left_x, y, ["Negociation", "Prospection", "CRM Salesforce", "Management"])

    # --- Right main column: interleaves with the sidebar on the y axis ---
    y = top
    y = _para(c, right_x, y, ["Raphael MARTIN"], font="Helvetica-Bold", size=16)
    y -= 6
    y = _para(c, right_x, y, ["Commercial Senior"], font="Helvetica", size=12)
    y -= 20
    y = _para(c, right_x, y, ["PROFIL"], font="Helvetica-Bold", size=11)
    y -= 6
    y = _para(c, right_x, y, [
        "Commercial confirme avec 10 ans d'experience",
        "dans la vente de produits de luxe et telecom.",
    ])
    y -= 20
    y = _para(c, right_x, y, ["EXPERIENCES"], font="Helvetica-Bold", size=11)
    y -= 8
    y = _para(c, right_x, y, ["Responsable Commercial - DIOR (2020-2024)"], font="Helvetica-Bold", size=10)
    y = _para(c, right_x, y, ["Developpement du portefeuille grands comptes."])
    y -= 12
    y = _para(c, right_x, y, ["Charge d'affaires - ORANGE (2016-2020)"], font="Helvetica-Bold", size=10)
    y = _para(c, right_x, y, ["Vente de solutions telecom aux entreprises."])
    y -= 12
    y = _para(c, right_x, y, ["Commercial - DANONE (2014-2016)"], font="Helvetica-Bold", size=10)
    y = _para(c, right_x, y, ["Prospection et fidelisation clients GMS."])
    y -= 20
    y = _para(c, right_x, y, ["FORMATION"], font="Helvetica-Bold", size=11)
    y -= 8
    y = _para(c, right_x, y, ["Master Commerce - Sorbonne (2014)"])
    y = _para(c, right_x, y, ["Licence Gestion - ESUP (2012)"])

    c.showPage()
    c.save()


def make_one_column_cv(path):
    c = canvas.Canvas(path, pagesize=A4)
    x = 50
    y = PAGE_H - 70
    y = _para(c, x, y, ["Sophie BERNARD"], font="Helvetica-Bold", size=16)
    y -= 6
    y = _para(c, x, y, ["Ingenieure Logiciel"], font="Helvetica", size=12)
    y -= 18
    y = _para(c, x, y, ["sophie.bernard@email.com  -  +33 7 98 76 54 32  -  Lyon"])
    y -= 22
    y = _para(c, x, y, ["EXPERIENCES"], font="Helvetica-Bold", size=11)
    y -= 8
    y = _para(c, x, y, ["Lead Developer - CAPGEMINI (2019-2024)"], font="Helvetica-Bold", size=10)
    y = _para(c, x, y, ["Conception de microservices Python et Java."])
    y -= 12
    y = _para(c, x, y, ["Developpeuse - ATOS (2015-2019)"], font="Helvetica-Bold", size=10)
    y = _para(c, x, y, ["Developpement d'applications web."])
    y -= 22
    y = _para(c, x, y, ["FORMATION"], font="Helvetica-Bold", size=11)
    y -= 8
    y = _para(c, x, y, ["Diplome d'ingenieur - INSA Lyon (2015)"])
    y -= 22
    y = _para(c, x, y, ["COMPETENCES"], font="Helvetica-Bold", size=11)
    y -= 8
    y = _para(c, x, y, ["Python, Java, Docker, Kubernetes, React"])
    c.showPage()
    c.save()


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    two = os.path.join(out_dir, "cv_two_column.pdf")
    one = os.path.join(out_dir, "cv_one_column.pdf")
    make_two_column_cv(two)
    make_one_column_cv(one)
    print("Wrote:", two)
    print("Wrote:", one)
