#!/usr/bin/env python3
"""Génère ../index.html à partir du gabarit et du contenu du sujet.

Le bloc <style>, le moteur Grading et le moteur applicatif sont repris tels
quels depuis gabarit-exercice-interactif.html ; seul le contenu du sujet
(textes, questions, barème, documents) est décrit ici.

Usage : python3 outils/generer_index.py
"""
import base64
import json
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
GABARIT = (ICI / "gabarit-exercice-interactif.html").read_text(encoding="utf-8")
SORTIE = ICI.parent / "index.html"

TITRE = "Binaire, hexadécimal, IPv4 et IPv6"

# ---------------------------------------------------------------------------
# Blocs repris du gabarit
# ---------------------------------------------------------------------------
STYLE = re.search(r"^<style>.*?</style>", GABARIT, re.S | re.M).group(0)
assert STYLE.startswith("<style>:root{")
GRADING = re.search(r"<script>/\*GRADING-START\*/.*?</script>", GABARIT, re.S).group(0)
APP = re.search(r"<script>\(function \(\) \{.*?</script>", GABARIT, re.S).group(0)

# ---------------------------------------------------------------------------
# Parties : la durée conseillée fixe la pondération
# ---------------------------------------------------------------------------
PARTS = [
    {"num": "1", "title": "Adresses IPv4 : binaire et décimal", "minutes": 15, "duration": "15 min"},
    {"num": "2", "title": "Adresses IPv6 : hexadécimal, binaire et décimal", "minutes": 20, "duration": "20 min"},
    {"num": "3", "title": "Nombres flottants sur 32 bits", "minutes": 25, "duration": "25 min"},
]
TOTAL_MIN = sum(p["minutes"] for p in PARTS)
DUREE_TXT = "1 h 00"

# Le chronomètre vire au jaune une fois la durée conseillée dépassée
APP = APP.replace("var CONSEIL_MIN = 300;", "var CONSEIL_MIN = %d;" % TOTAL_MIN)
assert ("var CONSEIL_MIN = %d;" % TOTAL_MIN) in APP

# ---------------------------------------------------------------------------
# Correcteurs réutilisables
# ---------------------------------------------------------------------------
BITS = {"label": "bits", "accept": ["bit", "bits"]}
OCTETS = {"label": "octets", "accept": ["octet", "octets"]}


def bits(n):
    """Nombre de bits, unité notée ; l'équivalent exact en octets est accepté."""
    g = {"type": "num", "value": n, "absTol": 0, "unit": BITS}
    if n % 8 == 0:
        g["variants"] = [{"value": n // 8, "absTol": 0, "unit": OCTETS, "strictUnit": True}]
    return g


def entier(n, *autres):
    g = {"type": "num", "value": n, "absTol": 0}
    if autres:
        g["variants"] = [{"value": a, "absTol": 0} for a in autres]
    return g


def binaire(*formes):
    return {"type": "code", "equals": list(formes)}


def decimal(v):
    return {"type": "num", "value": v, "absTol": 0.0005}


H_BITS = ("Nombre entier. Saisis la valeur <strong>avec son unité</strong> : "
          "l'unité vaut la moitié des points de la question.")
H_ENTIER = "Nombre entier."
H_FLOAT = ("Donne la valeur décimale exacte, avec son signe "
           "(virgule ou point décimal acceptés).")

# ---------------------------------------------------------------------------
# Contenu : parties > groupes > questions
# ---------------------------------------------------------------------------
FLOAT_SVG = """<svg viewBox="0 0 640 96" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Organisation des 32 bits d'un nombre flottant : 1 bit de signe, 8 bits d'exposant, 23 bits de mantisse">
<g font-family="Bahnschrift, 'Roboto Condensed', Arial Narrow, sans-serif" text-anchor="middle">
<rect x="10" y="10" width="40" height="46" fill="#FFF3C4" stroke="#1C2530" stroke-width="2"/>
<rect x="50" y="10" width="160" height="46" fill="#E6EEF8" stroke="#1C2530" stroke-width="2"/>
<rect x="210" y="10" width="420" height="46" fill="#E2F1E7" stroke="#1C2530" stroke-width="2"/>
<text x="30" y="40" font-size="18" font-weight="700" fill="#1C2530">S</text>
<text x="130" y="40" font-size="18" font-weight="700" fill="#1C2530">Exposant · 8 bits</text>
<text x="420" y="40" font-size="18" font-weight="700" fill="#1C2530">Mantisse · 23 bits</text>
<text x="30" y="78" font-size="13" fill="#46525C">bit 31</text>
<text x="130" y="78" font-size="13" fill="#46525C">bits 30 → 23</text>
<text x="420" y="78" font-size="13" fill="#46525C">bits 22 → 0</text>
</g></svg>"""

FLOAT_REGLES = """<ul>
<li><strong>Signe</strong> : <code>0</code> = positif, <code>1</code> = négatif.</li>
<li><strong>Exposant</strong> : exposant réel = valeur des 8 bits d'exposant − 127 (décalage).</li>
<li><strong>Mantisse</strong> : on lit <code>1,mantisse</code> en binaire ; les bits après la virgule valent ½, ¼, ⅛, 1/16…</li>
<li><strong>Valeur</strong> = signe × (1,mantisse)<sub>2</sub> × 2<sup>exposant − 127</sup>.</li>
</ul>"""

FLOAT_EXEMPLE = ("<code>0 10000010 11000000000000000000000</code> : signe +, exposant 130 − 127 = 3, "
                 "mantisse 1,11<sub>2</sub> = 1,75 → +1,75 × 2<sup>3</sup> = <strong>14</strong>.")

CONTENU = [
    {
        "part": "1",
        "intro": "<p>Une adresse IPv4 s'écrit en <strong>4 parties</strong> séparées par des points. Chaque partie est un "
                 "<strong>octet</strong>, qui va de <code>0</code> à <code>255</code> en décimal : la plage totale va de "
                 "<code>0.0.0.0</code> à <code>255.255.255.255</code>.</p>",
        "groups": [
            {"title": "Réseau d'un particulier : <code>192.168.1.x</code> (x = numéro d'un appareil)",
             "docs": ["DP1", "DT1"],
             "qs": [
                 {"id": "q1_1", "label": "Q1.1", "pts": 1,
                  "stem": "« x » peut prendre une valeur de 0 à 255. Sur combien de bits est-il codé en binaire ?",
                  "hint": H_BITS, "grader": bits(8),
                  "expected": "8 bits (soit 1 octet)",
                  "why": "<p>x peut prendre <strong>256 valeurs</strong> distinctes (de 0 à 255). Avec n bits on code "
                         "2<sup>n</sup> valeurs : 2<sup>7</sup> = 128 ne suffit pas, 2<sup>8</sup> = 256 convient exactement.</p>"
                         "<p>Il faut donc <strong>8 bits</strong>, c'est-à-dire un octet.</p>"},
                 {"id": "q1_2", "label": "Q1.2", "pts": 2,
                  "stem": "L'adresse de mon ordinateur est <code>192.168.1.2</code>. Écris cette adresse en binaire.",
                  "hint": "Chaque octet sur 8 bits, zéros de tête compris. Les points et les espaces sont facultatifs.",
                  "grader": binaire("11000000101010000000000100000010"),
                  "expected": "<code>11000000.10101000.00000001.00000010</code>",
                  "why": "<p>On convertit chaque octet séparément, en décomposant en puissances de 2 (128, 64, 32, 16, 8, 4, 2, 1) :</p>"
                         "<ul><li>192 = 128 + 64 → <code>11000000</code></li>"
                         "<li>168 = 128 + 32 + 8 → <code>10101000</code></li>"
                         "<li>1 → <code>00000001</code></li>"
                         "<li>2 → <code>00000010</code></li></ul>"
                         "<p>Chaque octet garde ses 8 bits : les zéros de tête font partie de l'adresse.</p>"},
                 {"id": "q1_3", "label": "Q1.3", "pts": 1,
                  "stem": "Combien d'appareils différents peut-on relier sur ce réseau <code>192.168.1.x</code> ?",
                  "hint": H_ENTIER, "grader": entier(256, 254),
                  "expected": "256 (254 en pratique)",
                  "why": "<p>x est codé sur 8 bits : 2<sup>8</sup> = <strong>256</strong> valeurs possibles, donc 256 adresses.</p>"
                         "<p>Précision réseau : deux adresses sont réservées (l'adresse du réseau <code>.0</code> et l'adresse "
                         "de diffusion <code>.255</code>), soit <strong>254</strong> appareils réellement adressables. "
                         "Les deux réponses sont acceptées.</p>"},
             ]},
            {"title": "Réseau d'une petite entreprise : <code>128.16.x.y</code>",
             "docs": ["DT1"],
             "qs": [
                 {"id": "q1_4", "label": "Q1.4", "pts": 1,
                  "stem": "« x » et « y » vont chacun de 0 à 255. Sur combien de bits au total la partie « x.y » de l'adresse est-elle codée ?",
                  "hint": H_BITS, "grader": bits(16),
                  "expected": "16 bits (soit 2 octets)",
                  "why": "<p>x occupe 8 bits et y occupe 8 bits : 8 + 8 = <strong>16 bits</strong>.</p>"},
                 {"id": "q1_5", "label": "Q1.5", "pts": 1,
                  "stem": "Combien d'appareils différents peut-on relier sur ce réseau <code>128.16.x.y</code> ?",
                  "hint": H_ENTIER + " Les espaces entre milliers sont acceptés.",
                  "grader": entier(65536, 65534),
                  "expected": "65 536 (65 534 en pratique)",
                  "why": "<p>16 bits donnent 2<sup>16</sup> = 256 × 256 = <strong>65 536</strong> combinaisons.</p>"
                         "<p>En retirant l'adresse du réseau et l'adresse de diffusion, il reste <strong>65 534</strong> "
                         "appareils adressables. Les deux réponses sont acceptées.</p>"},
             ]},
            {"title": "Généralisation : <code>w.x.y.z</code>, chaque octet de 0 à 255",
             "docs": ["DT1"],
             "qs": [
                 {"id": "q1_6", "label": "Q1.6", "pts": 1,
                  "stem": "Si les 4 octets <code>w.x.y.z</code> peuvent tous être choisis, sur combien de bits l'adresse complète est-elle codée ?",
                  "hint": H_BITS, "grader": bits(32),
                  "expected": "32 bits (soit 4 octets)",
                  "why": "<p>4 octets × 8 bits = <strong>32 bits</strong> : c'est la taille d'une adresse IPv4.</p>"},
                 {"id": "q1_7", "label": "Q1.7", "pts": 1,
                  "stem": "Combien d'appareils différents peut-on relier sur Internet avec la norme IPv4 ?",
                  "hint": "Donne le nombre entier exact. Les espaces entre milliers sont acceptés.",
                  "grader": entier(4294967296),
                  "expected": "2<sup>32</sup> = 4 294 967 296",
                  "why": "<p>32 bits donnent 2<sup>32</sup> = 256<sup>4</sup> = <strong>4 294 967 296</strong> adresses, "
                         "soit environ 4,3 milliards.</p>"
                         "<p>C'est moins d'une adresse par habitant de la planète, alors que chacun possède plusieurs "
                         "appareils connectés : d'où le passage à IPv6.</p>"},
             ]},
        ],
    },
    {
        "part": "2",
        "intro": "<p>Une adresse IPv6 s'écrit en <strong>8 parties</strong> séparées par des « : ». Chaque partie est écrite "
                 "en hexadécimal, de <code>0000</code> à <code>FFFF</code>. Exemple : "
                 "<code>2001:0db8:0000:85a3:0010:0a0b:8001:ec1f</code>.</p>",
        "groups": [
            {"title": "Préliminaires : le chiffre hexadécimal <code>E</code>",
             "docs": ["DT1"],
             "qs": [
                 {"id": "q2_1", "label": "Q2.1", "pts": 1,
                  "stem": "Convertis le chiffre hexadécimal <code>E</code> en décimal.",
                  "hint": H_ENTIER, "grader": entier(14),
                  "expected": "14",
                  "why": "<p>En hexadécimal, après 9 on continue avec des lettres : A = 10, B = 11, C = 12, D = 13, "
                         "<strong>E = 14</strong>, F = 15.</p>"},
                 {"id": "q2_2", "label": "Q2.2", "pts": 1,
                  "stem": "Convertis ce même chiffre <code>E</code> en binaire.",
                  "hint": "Écris uniquement les bits ; les espaces sont facultatifs.",
                  "grader": binaire("1110", "00001110"),
                  "expected": "<code>1110</code>",
                  "why": "<p>E = 14 = 8 + 4 + 2, soit <code>1110</code> en binaire (sur 4 bits).</p>"},
                 {"id": "q2_3", "label": "Q2.3", "pts": 1,
                  "stem": "Combien faut-il de bits pour coder un chiffre hexadécimal ?",
                  "hint": H_BITS, "grader": bits(4),
                  "expected": "4 bits",
                  "why": "<p>Un chiffre hexadécimal prend 16 valeurs (de 0 à F). Or 16 = 2<sup>4</sup> : "
                         "<strong>4 bits</strong> suffisent et sont nécessaires.</p>"
                         "<p>C'est pour cela que l'hexadécimal est si pratique : chaque chiffre correspond exactement à 4 bits.</p>"},
             ]},
            {"title": "Étude d'un des 8 éléments d'une adresse IPv6 : l'élément <code>ec1f</code>",
             "docs": ["DT1"],
             "qs": [
                 {"id": "q2_4", "label": "Q2.4", "pts": 2,
                  "stem": "Convertis le nombre hexadécimal <code>ec1f</code> en décimal.",
                  "hint": H_ENTIER + " Les espaces entre milliers sont acceptés.",
                  "grader": entier(60447),
                  "expected": "60 447",
                  "why": "<p>Chaque chiffre est pondéré par une puissance de 16, de droite à gauche :</p>"
                         "<p>e × 16<sup>3</sup> + c × 16<sup>2</sup> + 1 × 16<sup>1</sup> + f × 16<sup>0</sup></p>"
                         "<p>= 14 × 4 096 + 12 × 256 + 1 × 16 + 15 × 1</p>"
                         "<p>= 57 344 + 3 072 + 16 + 15 = <strong>60 447</strong>.</p>"},
                 {"id": "q2_5", "label": "Q2.5", "pts": 2,
                  "stem": "Convertis <code>ec1f</code> en binaire.",
                  "hint": "Écris les 16 bits ; les espaces sont facultatifs.",
                  "grader": binaire("1110110000011111"),
                  "expected": "<code>1110 1100 0001 1111</code>",
                  "why": "<p>Chaque chiffre hexadécimal se traduit directement par 4 bits :</p>"
                         "<ul><li>e = 14 → <code>1110</code></li><li>c = 12 → <code>1100</code></li>"
                         "<li>1 → <code>0001</code></li><li>f = 15 → <code>1111</code></li></ul>"
                         "<p>On met les groupes bout à bout : <code>1110 1100 0001 1111</code>. "
                         "Le « 1 » garde ses zéros de tête, sinon les bits suivants seraient décalés.</p>"},
                 {"id": "q2_6", "label": "Q2.6", "pts": 1,
                  "stem": "Sur combien de bits un élément d'adresse IPv6 (comme <code>ec1f</code>) est-il codé ?",
                  "hint": H_BITS, "grader": bits(16),
                  "expected": "16 bits (soit 2 octets)",
                  "why": "<p>4 chiffres hexadécimaux × 4 bits = <strong>16 bits</strong> par élément.</p>"},
             ]},
            {"title": "Généralisation",
             "docs": ["DP1"],
             "qs": [
                 {"id": "q2_7", "label": "Q2.7", "pts": 1,
                  "stem": "Sur combien de bits une adresse IPv6 complète est-elle codée ?",
                  "hint": H_BITS, "grader": bits(128),
                  "expected": "128 bits (soit 16 octets)",
                  "why": "<p>8 éléments × 16 bits = <strong>128 bits</strong>, quatre fois plus qu'une adresse IPv4.</p>"},
                 {"id": "q2_8", "label": "Q2.8", "pts": 1,
                  "stem": "Combien d'appareils différents peut-on relier sur Internet avec la norme IPv6 ?",
                  "hint": "Écris le résultat en notation scientifique, arrondi au dixième (par exemple <code>1,2 × 10^5</code> ou <code>1,2e5</code>).",
                  "grader": {"type": "num", "value": 3.402823669209385e38, "relTol": 0.015},
                  "expected": "2<sup>128</sup> ≈ 3,4 × 10<sup>38</sup>",
                  "why": "<p>128 bits donnent 2<sup>128</sup> adresses, soit exactement "
                         "340 282 366 920 938 463 463 374 607 431 768 211 456.</p>"
                         "<p>En notation scientifique : <strong>3,4 × 10<sup>38</sup></strong>. "
                         "C'est environ 7,9 × 10<sup>28</sup> fois plus qu'avec IPv4.</p>"},
             ]},
        ],
    },
    {
        "part": "3",
        "intro": "<p>Un nombre à virgule au format <em>float</em> occupe 32 bits, répartis en trois champs :</p>"
                 '<figure class="fig">' + FLOAT_SVG + "</figure>" + FLOAT_REGLES +
                 "<p><em>Exemple du cours :</em> " + FLOAT_EXEMPLE + "</p>",
        "groups": [
            {"title": "Retrouve la valeur décimale des nombres flottants suivants",
             "docs": ["DT2"],
             "qs": [
                 {"id": "q3_1", "label": "Q3.1", "pts": 2,
                  "stem": "<code>1 10000010 11110100000000000000000</code>",
                  "hint": H_FLOAT, "grader": decimal(-15.625),
                  "expected": "−15,625",
                  "why": "<ul><li><strong>Signe</strong> : bit 1 → nombre <strong>négatif</strong>.</li>"
                         "<li><strong>Exposant</strong> : <code>10000010</code> = 128 + 2 = 130 ; exposant réel = 130 − 127 = 3.</li>"
                         "<li><strong>Mantisse</strong> : 1,111101<sub>2</sub> = 1 + ½ + ¼ + ⅛ + 1/16 + 1/64 = 1,953125.</li></ul>"
                         "<p>Valeur = −1,953125 × 2<sup>3</sup> = <strong>−15,625</strong>.</p>"},
                 {"id": "q3_2", "label": "Q3.2", "pts": 2,
                  "stem": "<code>0 10001000 01101100001000000000000</code>",
                  "hint": H_FLOAT, "grader": decimal(728.25),
                  "expected": "728,25",
                  "why": "<ul><li><strong>Signe</strong> : bit 0 → nombre <strong>positif</strong>.</li>"
                         "<li><strong>Exposant</strong> : <code>10001000</code> = 128 + 8 = 136 ; exposant réel = 136 − 127 = 9.</li>"
                         "<li><strong>Mantisse</strong> : 1,01101100001<sub>2</sub> = 1 + ¼ + ⅛ + 1/32 + 1/64 + 1/2048 = 1,42236328125.</li></ul>"
                         "<p>Valeur = +1,42236328125 × 2<sup>9</sup> = <strong>728,25</strong>.</p>"
                         "<p>Raccourci : décaler la virgule de 9 rangs donne 1011011000,01<sub>2</sub> = 728 + ¼.</p>"},
                 {"id": "q3_3", "label": "Q3.3", "pts": 2,
                  "stem": "<code>11000010000011100000000000000000</code>",
                  "hint": "Les 32 bits sont donnés d'un seul bloc : découpe-les en 1 + 8 + 23. " + H_FLOAT,
                  "grader": decimal(-35.5),
                  "expected": "−35,5",
                  "why": "<p>Découpage : <code>1 | 10000100 | 00011100000000000000000</code>.</p>"
                         "<ul><li><strong>Signe</strong> : bit 1 → nombre <strong>négatif</strong>.</li>"
                         "<li><strong>Exposant</strong> : <code>10000100</code> = 128 + 4 = 132 ; exposant réel = 132 − 127 = 5.</li>"
                         "<li><strong>Mantisse</strong> : 1,000111<sub>2</sub> = 1 + 1/16 + 1/32 + 1/64 = 1,109375.</li></ul>"
                         "<p>Valeur = −1,109375 × 2<sup>5</sup> = <strong>−35,5</strong>.</p>"},
             ]},
        ],
    },
]

# ---------------------------------------------------------------------------
# Documents (rail de droite)
# ---------------------------------------------------------------------------
DOCS = [
    {"key": "DP1", "kind": "Dossier présentation", "title": "DP1 : adresses IPv4 et IPv6", "dt": False,
     "html": """<h3>À quoi sert une adresse IP ?</h3>
<p>Chaque appareil connecté à un réseau (ordinateur, téléphone, imprimante, objet connecté) possède une <strong>adresse IP</strong> qui permet de lui acheminer les données, comme une adresse postale permet d'acheminer le courrier.</p>
<h3>IPv4</h3>
<p>La norme historique, IPv4, écrit une adresse en <strong>4 nombres décimaux</strong> séparés par des points, chacun compris entre 0 et 255. Exemple : <code>192.168.1.2</code>.</p>
<p>Les réseaux domestiques utilisent souvent des adresses de la forme <code>192.168.1.x</code>, où seule la dernière partie change d'un appareil à l'autre.</p>
<h3>IPv6</h3>
<p>Face à la multiplication des appareils connectés, la norme IPv6 a été introduite. Une adresse IPv6 s'écrit en <strong>8 groupes de 4 chiffres hexadécimaux</strong>, séparés par des « : ». Exemple : <code>2001:0db8:0000:85a3:0010:0a0b:8001:ec1f</code>.</p>
<p>Pour alléger l'écriture, on peut omettre les zéros de tête d'un groupe (<code>0db8</code> → <code>db8</code>) et remplacer une seule suite de groupes nuls par « :: ».</p>"""},
    {"key": "DT1", "kind": "Dossier technique", "title": "DT1 : bases de numération", "dt": True,
     "html": """<h3>Binaire (base 2)</h3>
<p>Chaque bit a un poids qui est une puissance de 2, en partant de la droite :</p>
<div class="recap-wrap" style="padding:0"><table class="t"><thead><tr><th>Rang</th><th>7</th><th>6</th><th>5</th><th>4</th><th>3</th><th>2</th><th>1</th><th>0</th></tr></thead>
<tbody><tr><th>Poids</th><td>2<sup>7</sup> = 128</td><td>2<sup>6</sup> = 64</td><td>2<sup>5</sup> = 32</td><td>2<sup>4</sup> = 16</td><td>2<sup>3</sup> = 8</td><td>2<sup>2</sup> = 4</td><td>2<sup>1</sup> = 2</td><td>2<sup>0</sup> = 1</td></tr></tbody></table></div>
<p><strong>Décimal → binaire</strong> : on retire la plus grande puissance de 2 possible, et on recommence. Exemple : 45 = 32 + 8 + 4 + 1 → <code>00101101</code> sur 8 bits.</p>
<p><strong>Nombre de valeurs</strong> : avec n bits, on code 2<sup>n</sup> valeurs différentes, de 0 à 2<sup>n</sup> − 1.</p>
<h3>Hexadécimal (base 16)</h3>
<p>Seize symboles : les chiffres 0 à 9, puis les lettres A, B, C, D, E, F (majuscules ou minuscules). Chaque chiffre a pour poids une puissance de 16 :</p>
<div class="recap-wrap" style="padding:0"><table class="t"><thead><tr><th>Rang</th><th>3</th><th>2</th><th>1</th><th>0</th></tr></thead>
<tbody><tr><th>Poids</th><td>16<sup>3</sup> = 4 096</td><td>16<sup>2</sup> = 256</td><td>16<sup>1</sup> = 16</td><td>16<sup>0</sup> = 1</td></tr></tbody></table></div>
<p>Exemple : <code>1A</code> = 1 × 16 + 10 × 1 = 26.</p>
<p><strong>Hexadécimal ↔ binaire</strong> : chaque chiffre hexadécimal se traduit par un groupe de bits de même longueur, que l'on met bout à bout.</p>"""},
    {"key": "DT2", "kind": "Dossier technique", "title": "DT2 : format float 32 bits", "dt": True,
     "html": "<h3>Organisation des 32 bits</h3><figure class=\"fig\">" + FLOAT_SVG + "</figure>" + FLOAT_REGLES +
             "<h3>Exemple</h3><p>" + FLOAT_EXEMPLE + "</p>"
             "<h3>Valeur des bits de mantisse</h3>"
             "<div class=\"recap-wrap\" style=\"padding:0\"><table class=\"t\"><thead><tr><th>Bit après la virgule</th><th>1<sup>er</sup></th><th>2<sup>e</sup></th><th>3<sup>e</sup></th><th>4<sup>e</sup></th><th>5<sup>e</sup></th><th>6<sup>e</sup></th></tr></thead>"
             "<tbody><tr><th>Poids</th><td>0,5</td><td>0,25</td><td>0,125</td><td>0,0625</td><td>0,03125</td><td>0,015625</td></tr></tbody></table></div>"},
]

# ---------------------------------------------------------------------------
# Illustration d'accueil (SVG intégré en data URI)
# ---------------------------------------------------------------------------
def hero_svg():
    f = "font-family=\"Bahnschrift, 'Roboto Condensed', 'Arial Narrow', sans-serif\""
    mono = "font-family=\"Consolas, 'DejaVu Sans Mono', monospace\""
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">',
           '<rect width="900" height="420" fill="#FFFFFF"/>',
           '<g stroke="#D3D8D5" stroke-width="1">']
    for x in range(0, 901, 30):
        out.append('<line x1="%d" y1="0" x2="%d" y2="420"/>' % (x, x))
    for y in range(0, 421, 30):
        out.append('<line x1="0" y1="%d" x2="900" y2="%d"/>' % (y, y))
    out.append("</g>")
    # IPv4
    out.append('<text x="30" y="46" %s font-size="20" font-weight="700" fill="#1C2530">IPv4 · 32 bits</text>' % f)
    octets = [192, 168, 1, 2]
    for i, o in enumerate(octets):
        x = 30 + i * 212
        out.append('<rect x="%d" y="62" width="196" height="96" fill="#FFF3C4" stroke="#1C2530" stroke-width="2"/>' % x)
        out.append('<text x="%d" y="102" %s font-size="30" font-weight="700" text-anchor="middle" fill="#1C2530">%d</text>' % (x + 98, f, o))
        out.append('<text x="%d" y="140" %s font-size="22" text-anchor="middle" fill="#1F5FA8">%s</text>' % (x + 98, mono, format(o, "08b")))
        if i < 3:
            out.append('<circle cx="%d" cy="110" r="4" fill="#1C2530"/>' % (x + 204))
    # IPv6
    out.append('<text x="30" y="210" %s font-size="20" font-weight="700" fill="#1C2530">IPv6 · 128 bits</text>' % f)
    groupes = "2001:0db8:0000:85a3:0010:0a0b:8001:ec1f".split(":")
    for i, g in enumerate(groupes):
        x = 30 + i * 106
        last = i == 7
        out.append('<rect x="%d" y="226" width="98" height="46" fill="%s" stroke="#1C2530" stroke-width="%s"/>'
                   % (x, "#F2B705" if last else "#E6EEF8", "3" if last else "1.5"))
        out.append('<text x="%d" y="257" %s font-size="22" font-weight="700" text-anchor="middle" fill="#1C2530">%s</text>' % (x + 49, mono, g))
    out.append('<line x1="821" y1="274" x2="821" y2="300" stroke="#1C2530" stroke-width="2"/>')
    out.append('<line x1="420" y1="300" x2="821" y2="300" stroke="#1C2530" stroke-width="2"/>')
    nib = ["1110", "1100", "0001", "1111"]
    for i, n in enumerate(nib):
        x = 420 + i * 100
        out.append('<rect x="%d" y="312" width="92" height="40" fill="#E2F1E7" stroke="#1C2530" stroke-width="1.5"/>' % x)
        out.append('<text x="%d" y="339" %s font-size="20" text-anchor="middle" fill="#1B7A43">%s</text>' % (x + 46, mono, n))
        out.append('<text x="%d" y="372" %s font-size="15" text-anchor="middle" fill="#46525C">%s</text>' % (x + 46, mono, "ec1f"[i]))
    out.append('<text x="30" y="340" %s font-size="17" fill="#46525C">1 chiffre hexadécimal = 4 bits</text>' % f)
    out.append('<text x="30" y="400" %s font-size="17" fill="#46525C">float 32 bits : signe | exposant | mantisse</text>' % f)
    out.append('<rect x="420" y="384" width="12" height="24" fill="#FFF3C4" stroke="#1C2530"/>'
               '<rect x="432" y="384" width="96" height="24" fill="#E6EEF8" stroke="#1C2530"/>'
               '<rect x="528" y="384" width="276" height="24" fill="#E2F1E7" stroke="#1C2530"/>')
    out.append("</svg>")
    return "data:image/svg+xml;base64," + base64.b64encode("".join(out).encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------------------
# Rendu HTML
# ---------------------------------------------------------------------------
def fr(x, d=1):
    return ("%.*f" % (d, x)).replace(".", ",")


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


QCFG = {}
part_points = {p["num"]: 0 for p in PARTS}
for bloc in CONTENU:
    for g in bloc["groups"]:
        for q in g["qs"]:
            QCFG[q["id"]] = {"label": q["label"], "part": bloc["part"], "pts": q["pts"], "grader": q["grader"]}
            part_points[bloc["part"]] += q["pts"]
for p in PARTS:
    p["points"] = part_points[p["num"]]
NB_Q = len(QCFG)


def render_question(q):
    i = q["id"]
    return f"""
        <div class="q" id="{i}" data-q="{i}">
          <p class="q-stem"><span class="q-num">{q['label']}</span> <strong>{q['stem']}</strong></p>
          <p class="q-hint" id="h-{i}">{q['hint']}</p>
          <div class="q-row">
            <input type="text" class="q-input" id="in-{i}" aria-label="Réponse {q['label']}" aria-describedby="h-{i}" autocomplete="off" autocapitalize="off" spellcheck="false">
            <button type="button" class="btn btn-validate">Valider</button>
            <span class="q-status" aria-live="polite"></span>
            <span class="print-only pstat">Non validée : comptée fausse</span>
          </div>
          <p class="q-msg" role="alert"></p>
          <div class="q-expl" hidden>
            <p class="q-unit-msg" hidden></p>
            <p class="q-expected"><span>Réponse attendue :</span> {q['expected']}</p>
            <div class="q-why">{q['why']}</div>
          </div>
        </div>"""


def render_part(bloc):
    p = next(x for x in PARTS if x["num"] == bloc["part"])
    n = p["num"]
    poids = fr(p["minutes"] / TOTAL_MIN * 100)
    html = [f"""
  <section class="part" id="partie-{n}" aria-labelledby="t-partie-{n}">
    <header class="part-head"><div class="part-num" aria-hidden="true">{n}</div>
      <div><h2 id="t-partie-{n}"><span class="sr-only">Partie {n} : </span>{p['title']}</h2>
        <div class="duree">Durée conseillée : {p['duration']} · Barème : {p['points']} points, soit {poids} % de la note</div></div></header>
    <div class="part-body">
      {bloc['intro']}"""]
    for g in bloc["groups"]:
        labels = [q["label"] for q in g["qs"]]
        rng = labels[0] if len(labels) == 1 else labels[0] + "–" + labels[-1][1:]
        chips = " ".join(f'<button type="button" class="doc-chip" data-doc="{d}" aria-pressed="false">{d}</button>' for d in g["docs"])
        html.append(f"""
      <div class="qbar" role="group" aria-label="{rng}"><div class="qb-num">{rng}</div><div class="qb-docs">Documents à consulter : {chips}</div><div class="qb-ans">Répondre : ci-dessous</div><div class="qb-title">{g['title']}</div></div>""")
        html.extend(render_question(q) for q in g["qs"])
    html.append("""
    </div>
  </section>
""")
    return "".join(html)


def render_docs():
    rail, tabs, body = [], [], []
    prev_dt = None
    for d in DOCS:
        if prev_dt is False and d["dt"]:
            rail.append('  <div class="grp" aria-hidden="true"></div>')
        prev_dt = d["dt"]
        cls = "tab dt" if d["dt"] else "tab"
        rail.append(f'  <button type="button" class="{cls}" data-doc="{d["key"]}" aria-selected="false" title="{strip_tags(d["title"])}">{d["key"]}</button>')
        tabs.append(f'    <button type="button" data-doc="{d["key"]}" aria-selected="false">{d["key"]}</button>')
        body.append(f'    <section class="doc" id="doc-{d["key"]}" data-title="{d["title"]}" data-kind="{d["kind"]}">\n'
                    f'      <div class="doc-text">{d["html"]}</div>\n    </section>')
    return "\n".join(rail), "\n".join(tabs), "\n".join(body)


rail, tabs, docbody = render_docs()
parts_html = "".join(render_part(b) for b in CONTENU)
nb_docs = len(DOCS)
liste_docs = ", ".join(d["key"] for d in DOCS[:-1]) + " et " + DOCS[-1]["key"]

parts_js = json.dumps(PARTS, ensure_ascii=False)
qcfg_js = json.dumps(QCFG, ensure_ascii=False)

page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Fichier généré par outils/generer_index.py à partir de outils/gabarit-exercice-interactif.html : modifier le générateur, pas ce fichier. -->
<title>{TITRE} — exercice interactif</title>
<meta name="description" content="Conversions entre binaire, décimal et hexadécimal à partir des adresses IPv4 et IPv6, puis décodage de nombres flottants sur 32 bits.">
{STYLE}
</head>
<body class="no-mode">

<nav class="rail" aria-label="Dossiers de présentation et dossier technique">
{rail}
</nav>

<aside id="docpanel" aria-label="Documents du sujet" aria-hidden="true">
  <div class="dp-head">
    <h3 id="dp-title">Documents</h3>
    <button type="button" id="dp-out" aria-label="Réduire">−</button><span id="dp-zoom" class="small">100 %</span>
    <button type="button" id="dp-in" aria-label="Agrandir">+</button>
    <button type="button" id="dp-fit">Ajuster</button>
    <button type="button" id="dp-close">Fermer</button>
  </div>
  <div class="dp-tabs" role="tablist" aria-label="Choisir un document">
{tabs}
  </div>
  <div class="dp-body">
{docbody}
  </div>
</aside>

<section id="home" aria-labelledby="home-title">
  <div class="home-inner">
    <header class="home-head">
      <h1 id="home-title">{TITRE}</h1>
      <p class="home-sub">Comment un réseau numérote-t-il ses appareils ? En partant des adresses IPv4 puis IPv6, tu passes du décimal au binaire et à l'hexadécimal, avant de décoder des nombres à virgule stockés sur 32 bits. {NB_Q} questions, environ une heure de travail.</p>
    </header>
    <figure class="home-hero">
      <img src="{hero_svg()}" alt="Une adresse IPv4 192.168.1.2 décomposée en quatre octets binaires, une adresse IPv6 en huit groupes hexadécimaux dont le groupe ec1f traduit en quatre groupes de 4 bits, et les trois champs d'un nombre flottant." width="900" height="420">
      <figcaption>Une même information, trois écritures : décimal, binaire et hexadécimal.</figcaption>
    </figure>
    <div class="home-facts">
      <div><b>{len(PARTS)} parties</b><span>IPv4, IPv6, nombres flottants</span></div>
      <div><b>{DUREE_TXT}</b><span>durée conseillée, qui fixe la pondération</span></div>
      <div><b>{nb_docs} documents</b><span>{liste_docs} consultables</span></div>
      <div><b>0 tracé</b><span>uniquement des réponses saisies</span></div>
    </div>
    <h2 class="home-choose">Choisis ton mode de travail</h2>
    <div class="modes">
      <article class="mode-card">
        <div class="mc-head"><span class="mc-tag">Mode 1</span><h3>Mode entraînement</h3></div>
        <p class="mc-lead">Pour apprendre en avançant, question par question.</p>
        <ul><li>Chaque question se valide isolément ; la démarche corrigée s'affiche aussitôt.</li>
          <li>La note pondérée s'actualise en continu dans le bandeau.</li>
          <li>Les documents et le chronomètre restent disponibles, sans contrainte de temps.</li></ul>
        <button type="button" class="btn btn-mode" data-mode="training">Commencer l'entraînement</button>
      </article>
      <article class="mode-card exam">
        <div class="mc-head"><span class="mc-tag">Mode 2</span><h3>Mode examen</h3></div>
        <p class="mc-lead">Pour se placer dans les conditions d'une évaluation.</p>
        <ul><li>Aucune correction et aucune note pendant la composition ; les réponses restent modifiables.</li>
          <li>Le chronomètre tourne, à comparer à la durée conseillée.</li>
          <li>En fin de sujet, le bouton « J'ai fini, je fais corriger ma copie » dévoile d'un coup les corrections, les notes par partie et la note globale.</li></ul>
        <button type="button" class="btn btn-mode" data-mode="exam">Composer en mode examen</button>
      </article>
    </div>
    <p class="home-note small">Le mode se choisit une seule fois : pour en changer, recharge la page. Rien n'est enregistré sur l'ordinateur.</p>
  </div>
</section>

<main class="page">
  <section class="print-only print-summary">
    <p>Élève : <span class="print-nom"></span> | Copie imprimée le <span class="print-date"></span></p>
    <p>Mode : <span class="print-mode"></span> | Temps de rédaction : <strong class="print-time"></strong> (durée conseillée : {DUREE_TXT})</p>
    <p class="print-note-line">Note finale pondérée : <strong class="final-note"></strong></p>
    <p class="print-nograde">Copie non corrigée : les corrections et la note n'apparaissent qu'après la remise de la copie en mode examen.</p>
  </section>

  <header class="cartouche">
    <div class="title">
      <h1>{TITRE}</h1>
      <p>{NB_Q} questions notées (unités comprises), réparties en {len(PARTS)} parties pondérées par leur durée.</p></div>
    <div class="nom"><label for="nom-eleve">Nom et prénom</label><input id="nom-eleve" type="text" autocomplete="name"></div>
  </header>

  <div class="consignes">
    <p class="only-training"><strong>Mode entraînement.</strong> Réponds dans chaque champ puis clique sur « Valider » : une réponse validée est définitive et sa correction s'affiche aussitôt.</p>
    <p class="only-exam"><strong>Mode examen.</strong> Compose tout le sujet sans correction ni note : tes réponses restent modifiables jusqu'au bout. Le bouton « J'ai fini, je fais corriger ma copie », en fin de sujet, dévoile d'un coup les corrections, les notes par partie et la note globale.</p>
    <p><strong>Les unités sont notées.</strong> Quand une réponse porte une unité (le bit ou l'octet), la valeur vaut la moitié des points et l'unité l'autre moitié : une valeur juste écrite sans unité, ou avec une unité fausse, ne rapporte que la moitié des points.</p>
    <p>Les documents de présentation (DP) et techniques (DT) s'ouvrent avec les onglets sur le bord droit, ou avec les boutons des en-têtes de question.</p>
    <p><strong>Barème pondéré par la durée conseillée</strong> : chaque partie est notée sur 20, puis pèse au prorata de son temps. Le récapitulatif de fin de sujet donne le détail partie par partie.</p>
  </div>
{parts_html}
  <section class="recap" id="recap" aria-labelledby="t-recap">
    <header class="recap-head"><h2 id="t-recap">Récapitulatif et note finale</h2>
      <p class="small">Les questions non validées comptent comme fausses. Chaque partie est ramenée sur 20, puis pondérée par sa durée conseillée.</p></header>
    <div id="exam-submit-wrap">
      <p class="es-lead">Ta copie n'est pas encore corrigée : aucune réponse n'est verrouillée, tu peux encore revenir sur les questions.</p>
      <button type="button" class="btn btn-exam" id="exam-submit">J'ai fini, je fais corriger ma copie</button>
      <p class="es-warn" id="exam-warn" role="alert"></p>
    </div>
    <div id="recap-graded">
      <div class="recap-wrap">
        <table class="t recap-table">
          <thead><tr><th>Partie</th><th>Durée</th><th>Poids</th><th>Points</th><th>Note /20</th><th>Contribution</th></tr></thead>
          <tbody id="recap-body"></tbody>
          <tfoot><tr><th colspan="4">Note globale pondérée</th><th class="final-note"></th><th></th></tr></tfoot>
        </table>
      </div>
      <p class="final-detail small"></p>
    </div>
    <div class="recap-foot" id="recap-foot"><button type="button" class="btn btn-print">Imprimer ma copie</button>
      <span class="small no-print">L'impression reprend tes réponses, les corrections et ce récapitulatif.</span></div>
  </section>
</main>

<footer class="banner" aria-label="Suivi de la composition">
  <div class="score-block"><div class="lab">Note provisoire</div><div class="score" id="score-val">–<small>/20</small></div></div>
  <div class="exam-block"><div class="lab">Mode examen</div><div class="exam-state">Note masquée</div></div>
  <div class="timer-block"><div class="lab">Temps</div><div class="timer" id="timer-val">0:00:00</div></div>
  <div class="count" id="score-count" aria-live="polite"></div>
  <div class="spacer"></div>
  <button type="button" class="btn-docs" id="btn-docs">Documents</button>
</footer>

<script>window.__PARTS__ = {parts_js};
window.__QCFG__ = {qcfg_js};
window.__SKCFG__ = {{}};</script>
{GRADING}
{APP}
</body>
</html>
"""

SORTIE.write_text(page, encoding="utf-8")
print("Écrit :", SORTIE, "(%d octets)" % len(page.encode("utf-8")))
