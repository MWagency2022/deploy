"""Extrait l'erreur utile d'un log de build et l'inscrit dans le rapport.

Objectif : pouvoir comprendre et corriger dans Lovable sans jamais ouvrir les
logs GitHub. Le texte retenu est tronque et expurge de tout ce qui ressemble a
un identifiant.
"""
import os, re, sys
import mw_common as mw

log     = sys.argv[1]
etape   = sys.argv[2] if len(sys.argv) > 2 else 'build'   # dependances | build
MAX_LIGNES = 30
MAX_CARS   = 2500

MOTIFS_SENSIBLES = [
    (re.compile(r'(?i)(://[^:/@\s]+):([^@\s]+)@'), r'\1:***@'),
    (re.compile(r'(?i)\b(password|passwd|pwd|secret|token|api[-_]?key|auth)'
                r'(\s*[:=]\s*)(\S+)'), r'\1\2***'),
    (re.compile(r'\b[A-Za-z0-9+/]{40,}={0,2}\b'), '***'),
    (re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b'), '***'),
]

BRUIT = re.compile(
    r'(?i)^(npm (notice|WARN deprecated|warn deprecated)|'
    r'\s*$|added \d+ packages|found \d+ vulnerabilities|'
    r'run `npm audit`|npm fund|\s*\d+ packages are looking for funding)')

INTERESSANT = re.compile(
    r'(?i)(error|erreur|failed|échec|echec|cannot|not found|undefined|'
    r'unexpected|missing|ENOENT|EACCES|SyntaxError|TypeError|'
    r'Module not found|Transform failed|npm ERR!)')


def expurger(texte):
    for motif, remplacement in MOTIFS_SENSIBLES:
        texte = motif.sub(remplacement, texte)
    return texte


if not os.path.isfile(log):
    extrait = "(aucune sortie de build capturee)"
else:
    lignes = [l.rstrip() for l in open(log, encoding='utf-8', errors='replace')]
    utiles = [l for l in lignes if not BRUIT.match(l)]

    # On privilegie le voisinage des lignes d'erreur, sinon la fin du log.
    indices = [i for i, l in enumerate(utiles) if INTERESSANT.search(l)]
    if indices:
        debut = max(0, indices[0] - 3)
        fin = min(len(utiles), indices[-1] + 3)
        choisies = utiles[debut:fin]
        if len(choisies) > MAX_LIGNES:
            choisies = choisies[:MAX_LIGNES]
    else:
        choisies = utiles[-MAX_LIGNES:]

    extrait = expurger("\n".join(choisies))[:MAX_CARS].strip() or "(sortie vide)"

titre = ("L'installation des dependances a echoue."
         if etape == 'dependances' else "Le build du projet a echoue.")

r = mw.charger()
r['build'] = 'failed'
r['buildError'] = extrait
mw.probleme(r, 'BUILD', 'build', titre,
            "Corriger l'erreur ci-dessus dans Lovable, puis relancer.",
            trouve=extrait, categorie='lovable')
r['status_global'] = 'blocked'
mw.sauver(r)

print("Erreur de build enregistree dans le rapport :")
print("-" * 60)
print(extrait)
print("-" * 60)
