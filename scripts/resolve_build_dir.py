"""Detecte le dossier contenant le site statique produit par le build."""
import os, sys
import mw_common as mw

racine   = sys.argv[1] if len(sys.argv) > 1 else '.'
explicite = (sys.argv[2] if len(sys.argv) > 2 else '').strip()

CANDIDATS = ['dist/client', 'dist', 'build', 'out', '.output/public']


def exploitable(d):
    """Un build exploitable contient un index.html non vide et au moins un asset."""
    index = os.path.join(d, 'index.html')
    if not os.path.isfile(index):
        return False, "index.html absent"
    if os.path.getsize(index) < 200:
        return False, "index.html anormalement petit"
    contenu = open(index, encoding='utf-8', errors='replace').read()
    if '<html' not in contenu.lower():
        return False, "index.html ne contient pas de balise <html>"
    return True, ""


r = mw.charger()
trouve, raisons = None, []

if explicite:
    d = os.path.join(racine, explicite)
    ok, pourquoi = exploitable(d)
    if ok:
        trouve = explicite
    else:
        print(f"ERREUR : build_dir \"{explicite}\" impose mais inexploitable ({pourquoi})")
        mw.probleme(r, 'build', 'build_dir',
                    f"Le dossier impose \"{explicite}\" ne contient pas de site exploitable ({pourquoi}).",
                    "Corriger build_dir dans le fichier appelant, ou le retirer "
                    "pour laisser la detection automatique faire son travail.")
        r['build'] = 'failed'; r['status_global'] = 'blocked'
        mw.sauver(r); sys.exit(1)
else:
    for c in CANDIDATS:
        d = os.path.join(racine, c)
        if not os.path.isdir(d):
            raisons.append(f"{c} : dossier absent")
            continue
        ok, pourquoi = exploitable(d)
        raisons.append(f"{c} : {'exploitable' if ok else pourquoi}")
        if ok:
            trouve = c
            break

for l in raisons:
    print("  ", l)

if not trouve:
    print("\nPUBLICATION BLOQUEE")
    print("Aucun build statique exploitable n'a ete detecte.")
    mw.probleme(r, 'build', 'build_dir',
                "Aucun build statique exploitable n'a ete detecte "
                f"(essaye : {', '.join(CANDIDATS)}).",
                "Verifier que le build produit bien un index.html, "
                "et que le prerendu est active dans vite.config.")
    r['build'] = 'failed'; r['status_global'] = 'blocked'
    mw.sauver(r); sys.exit(1)

print(f"\nDossier de build retenu : {trouve}")
r['build'] = 'ok'; r['buildDir'] = trouve
mw.sauver(r)

sortie = os.environ.get('GITHUB_OUTPUT')
if sortie:
    open(sortie, 'a', encoding='utf-8').write(f"build_dir={trouve}\n")
