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


def make_long_cv(path):
    """Generate a multi-page CV PDF with entities spread far past the 384-token mark.

    Three 'landmark' employers (AIRBUS, THALES, BOUYGUES) and two 'landmark'
    schools (Universite Paris-Saclay, INSA Toulouse) are placed deliberately
    in the SECOND HALF of the document (after ~1 500 tokens of filler), so
    that the old single-pass GLiNER behaviour (truncated to 384 tokens) would
    miss them entirely.  The chunked extractor must find them all.
    """
    c = canvas.Canvas(path, pagesize=A4)
    x = 50
    leading = 13

    def section(title):
        c.setFont("Helvetica-Bold", 11)
        return title

    def body(lines, y):
        c.setFont("Helvetica", 9)
        for line in lines:
            if y < 60:
                c.showPage()
                y = PAGE_H - 60
                c.setFont("Helvetica", 9)
            c.drawString(x, y, line)
            y -= leading
        return y

    y = PAGE_H - 60

    # ------------------------------------------------------------------
    # Header  (clearly in chunk 0 -- always captured even by old code)
    # ------------------------------------------------------------------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "Alexandre MOREAU"); y -= 20
    c.setFont("Helvetica", 11)
    c.drawString(x, y, "Ingenieur Senior en Systemes Embarques"); y -= 14
    c.drawString(x, y, "alexandre.moreau@email.fr  |  +33 6 11 22 33 44  |  Toulouse"); y -= 20

    # ------------------------------------------------------------------
    # PROFIL (chunk 0 -- early content to fill initial token budget)
    # ------------------------------------------------------------------
    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, "PROFIL"); y -= 14
    y = body([
        "Ingenieur confirme avec 18 ans d experience dans le domaine des systemes",
        "embarques critiques, de la navigation aerospatiale et de la defense.",
        "Expert en architecture logicielle temps-reel, protocoles avioniques et",
        "integration systeme. Habitue a travailler en environnement DO-178C et",
        "exigences EUROCAE. Capacite a manager des equipes pluridisciplinaires",
        "et a piloter des projets complexes en mode Agile/SAFe.",
        "Bilingue francais-anglais, notions d allemand technique.",
        "Mobilite internationale acceptee. Habilitation secret defense en cours.",
    ], y)
    y -= 10

    # ------------------------------------------------------------------
    # EXPERIENCES -- early block (chunk 0/1, well-known anchor companies)
    # ------------------------------------------------------------------
    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, "EXPERIENCES PROFESSIONNELLES"); y -= 14

    # Experience 1  -- DASSAULT AVIATION  (chunk 0, should always be captured)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Architecte Logiciel Avionique -- DASSAULT AVIATION  (2018 - 2024)"); y -= 12
    y = body([
        "Responsable de l architecture du systeme de gestion de vol (FMS) du Falcon 10X.",
        "Coordination de 12 ingenieurs repartis sur 3 sites (Bordeaux, Marignane, Paris).",
        "Mise en place du processus de certification DO-178C DAL A pour les modules critiques.",
        "Revue de conception avec les autorites de certification (EASA / FAA).",
        "Reduction de 30 % du temps de build grace a l optimisation du pipeline CI/CD.",
        "Technologies : Ada 2012, C++17, Python 3, ARINC 429, MIL-STD-1553.",
        "Outils : DOORS, Rhapsody, Jenkins, Coverity, LDRA Testbed.",
        "Formation et accompagnement des nouveaux membres de l equipe (onboarding).",
    ], y)
    y -= 10

    # Experience 2 -- SAFRAN ELECTRONICS  (chunk 0/1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Ingenieur Integration -- SAFRAN ELECTRONICS & DEFENSE  (2015 - 2018)"); y -= 12
    y = body([
        "Integration et validation des cartes electroniques embarquees pour INS/GPS.",
        "Developpement de bancs de test automatises sous Python et LabVIEW.",
        "Ecriture des procedures de qualification environnementale (vibrations, thermique).",
        "Participation aux campagnes d essais en vol sur C295 et ATR 72.",
        "Suivi des non-conformites et gestion des actions correctives (8D).",
        "Redaction des dossiers de justification de conception (DJC).",
        "Interface avec les clients avionneurs (Airbus Helicopters, Leonardo).",
    ], y)
    y -= 10

    # Experience 3 -- THALES GROUP (chunk 1/2 -- mid document)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Ingenieur Logiciel Embarque -- THALES GROUP  (2012 - 2015)"); y -= 12
    y = body([
        "Conception et implementation de drivers bas niveau pour processeurs PowerPC.",
        "Portage de BSP VxWorks vers LynxOS-178 pour les calculateurs mission.",
        "Optimisation des latences temps-reel (< 50 us garanti en mode ARINC 653).",
        "Contribution aux travaux de normalisation ARINC 653 Part 2.",
        "Mise en place de la couverture de code MC/DC (100 % atteint sur les modules DO-178B).",
        "Collaboration avec les equipes systeme et electronique pour le BIT/BITE.",
        "Technologies : C89, Ada 95, VxWorks 6.9, LynxOS-178, Green Hills MULTI.",
    ], y)
    y -= 10

    # Experience 4 -- long filler to push next entries past token 700
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Ingenieur Developpement -- SAGEM DEFENSE SECURITE  (2009 - 2012)"); y -= 12
    y = body([
        "Developpement des algorithmes de traitement du signal pour centrales inertielles.",
        "Implementation Kalman etendu pour la fusion GPS/INS sur FPGA Xilinx Virtex-5.",
        "Verification formelle avec outils Astreet et Polyspace pour code embarque critique.",
        "Participation a la mise au point des algorithmes de calibration gyroscopique.",
        "Modelisation et simulation Matlab/Simulink de la chaine de traitement navigation.",
        "Generation automatique de code C certifiable depuis modeles Simulink (TargetLink).",
        "Integration sur banc de simulation Hardware-in-the-Loop (HIL).",
        "Redaction des specifications detaillees de conception (SDC) et des plans de tests.",
        "Participation aux revues de qualification (DRB, TRB) avec les representants DGA.",
    ], y)
    y -= 10

    # Experience 5 -- more filler
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Stagiaire R&D -- ONERA  (2006 - 2007)"); y -= 12
    y = body([
        "Stage de fin d etudes sur l estimation robuste d attitude par vision embarquee.",
        "Implementation d un filtre particulaire sur DSP TMS320C6713 pour suivi de cibles.",
        "Validation sur sequences video synthetiques et reelles (banc optique ONERA).",
        "Publication d un rapport de stage et presentation interne aux chercheurs ONERA.",
    ], y)
    y -= 16

    # ------------------------------------------------------------------
    # COMPETENCES TECHNIQUES (mid document -- pushes token count higher)
    # ------------------------------------------------------------------
    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, "COMPETENCES TECHNIQUES"); y -= 14
    y = body([
        "Langages        : Ada 2012, C/C++17, Python 3, VHDL, Matlab/Simulink",
        "RTOS            : VxWorks 6.9/7, LynxOS-178, RTEMS, FreeRTOS",
        "Protocoles bus  : ARINC 429, ARINC 664 (AFDX), MIL-STD-1553, CAN",
        "Normes          : DO-178C (DAL A-D), DO-254, ARP4754A, EUROCAE ED-12C",
        "Outils qualite  : LDRA, Polyspace, Cantata++, VectorCAST",
        "Gestion conf.   : Git, SVN, DOORS, IBM DOORS Next",
        "Cloud/DevOps    : Jenkins, GitLab CI, Docker, Kubernetes (notions)",
        "Langues         : Francais (natif), Anglais (C1 TOEIC 930), Allemand (A2)",
    ], y)
    y -= 16

    # ------------------------------------------------------------------
    # PROJETS NOTABLES (mid document)
    # ------------------------------------------------------------------
    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, "PROJETS NOTABLES"); y -= 14
    y = body([
        "Projet NGCMS (2021-2024) : Nouveau calculateur de gestion de mission pour",
        "avion de combat. Chef de projet logiciel, equipe de 8 personnes.",
        "Budget 2.4 M EUR, livraison en avance de 3 semaines.",
        "",
        "Projet GNSS-Integrity (2013-2015) : Integration d un moniteur d integrite SBAS",
        "dans le recepteur navigation critique. Certification RTCA DO-229D.",
        "Premier systeme certifie en Europe sur ce recepteur.",
        "",
        "Projet HIL-Factory (2010-2012) : Industrialisation du banc HIL mutualisé.",
        "Reduction des couts de simulation de 40 % et amelioration de la couverture",
        "des scenarios de test de 60 %. Deploiement sur 4 sites Sagem.",
    ], y)
    y -= 16

    # ------------------------------------------------------------------
    # CERTIFICATIONS & FORMATIONS COURTES
    # ------------------------------------------------------------------
    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, "CERTIFICATIONS"); y -= 14
    y = body([
        "Certified SAFe 5 Practitioner (Scaled Agile, 2022)",
        "DO-178C Advanced (Intacs / Elsys, 2020)",
        "ARINC 653 Partitioned RTOS Architecture (Wind River, 2019)",
        "Linux Kernel Internals & Device Drivers (Linux Foundation, 2018)",
        "Project Management Professional PMP (PMI, 2017)",
    ], y)
    y -= 16

    # ------------------------------------------------------------------
    # SECOND HALF -- landmark entities intentionally placed LATE
    # in the document (these are the ones the old single-pass missed)
    # ------------------------------------------------------------------

    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, "AUTRES MISSIONS & CONSULTANCES"); y -= 14

    # Landmark company 1: AIRBUS (late -- chunk 3+)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Consultant technique -- AIRBUS OPERATIONS SAS  (2024, mission 6 mois)"); y -= 12
    y = body([
        "Audit et remediation du process de verification logicielle pour A320neo FBW.",
        "Identification de 14 ecarts par rapport aux exigences DO-178C DAL A.",
        "Redaction du plan d actions correctives et suivi jusqu a la cloture.",
        "Formation des equipes sur les nouvelles exigences EASA AMC 20-115D.",
        "Livrable : rapport d audit, plan de remediation, sessions de formation (3 jours).",
    ], y)
    y -= 10

    # Landmark company 2: BOUYGUES (late -- chunk 3+)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Expert Systemes Embarques -- BOUYGUES TELECOM  (2023, mission 4 mois)"); y -= 12
    y = body([
        "Evaluation de la securite des firmwares equipements reseau (routeurs CPE).",
        "Analyse statique de code C/C++ avec Coverity et CodeQL.",
        "Revue des mecanismes de mise a jour securisee (secure boot, signature RSA-4096).",
        "Livrable : rapport de vulnerabilites, recommandations d architecture securisee.",
    ], y)
    y -= 16

    # ------------------------------------------------------------------
    # FORMATION  (late in document -- chunk 3/4)
    # ------------------------------------------------------------------
    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, "FORMATION"); y -= 14

    # Landmark school 1: Universite Paris-Saclay (late)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Master Recherche Automatique & Traitement du Signal"); y -= 12
    y = body([
        "Universite Paris-Saclay (anciennement Paris-Sud XI)  --  2007",
        "Mention Tres Bien -- Major de promotion (2 candidats sur 24 admis).",
        "Specialite : estimation, filtrage optimal, commande robuste.",
        "Stage : ONERA Chatillon -- estimation d attitude par vision embarquee.",
    ], y)
    y -= 10

    # Landmark school 2: INSA Toulouse (late)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Diplome d Ingenieur -- Genie Electrique & Informatique Industrielle"); y -= 12
    y = body([
        "INSA Toulouse  --  2005",
        "Option : Systemes Temps Reel et Embarques.",
        "Projet de fin d etudes : implementation FPGA d un codeur LDPC.",
        "Classement : 8e sur 120 etudiants de la promotion.",
    ], y)
    y -= 10

    # ------------------------------------------------------------------
    # CENTRES D INTERET
    # ------------------------------------------------------------------
    c.setFont("Helvetica-Bold", 11); c.drawString(x, y, "CENTRES D INTERET"); y -= 14
    y = body([
        "Pilote ULM (brevet obtenu 2019) -- randonnees aeriennes dans les Pyrenees.",
        "Photographie argentique -- developpement en chambre noire.",
        "Escalade -- niveau 6b en salle, 5c en falaise.",
        "Contribution open source : mainteneur du projet etl-pipeline (GitHub, 340 etoiles).",
    ], y)

    c.showPage()
    c.save()


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    two = os.path.join(out_dir, "cv_two_column.pdf")
    one = os.path.join(out_dir, "cv_one_column.pdf")
    long = os.path.join(out_dir, "cv_long.pdf")
    make_two_column_cv(two)
    make_one_column_cv(one)
    make_long_cv(long)
    print("Wrote:", two)
    print("Wrote:", one)
    print("Wrote:", long)
