"""Verifie que les pages publiques attendues existent reellement dans le build.

L'audit SEO ne sait controler que ce qui a ete produit. Cette verification-ci
attrape le cas inverse : une route qui aurait du sortir et qui manque, signe
d'un prerendu partiel ou inexistant.

La liste vient de "pages" dans mw-config.json, maintenue par Lovable.
"""
import json, os, re, sys
import mw_common as mw

racine  = sys.argv[1]
dossier = sys.argv[2]
domaine = (sys.argv[3] or '').rstrip('/')
mode    = sys.argv[4] if len(sys.argv) > 4 else 'rapport'

r = mw.charger()
chemin_cfg = os.path.join(racine, 'mw-config.json')

if not os.path.isfile(chemin_cfg):
    print("Pas de mw-config.json : verification des pages attendues ignoree.")
    sys.exit(0)

try:
    cfg = json.load(open(chemin_cfg, encoding='utf-8'))
except Exception:
    print("mw-config.json illisible : verification ignoree.")
    sys.exit(0)

attendues = cfg.get('pages')
if not attendues:
    print("Aucune liste \"pages\" dans mw-config.json : verification ignoree.")
    mw.info(r, "Liste des pages attendues absente de mw-config.json.")
    mw.sauver(r)
    sys.exit(0)

if not isinstance(attendues, list):
    print("\"pages\" doit etre une liste d'URLs relatives.")
    sys.exit(0)

sitemap = ''
chemin_sitemap = os.path.join(dossier, 'sitemap.xml')
if os.path.isfile(chemin_sitemap):
    sitemap = open(chemin_sitemap, encoding='utf-8', errors='replace').read()

print("=" * 68)
print(f" PAGES ATTENDUES - {len(attendues)} declaree(s) dans mw-config.json")
print("=" * 68)


def candidats(url):
    """Fichiers acceptables pour une URL logique."""
    chemin = url.strip()
    if not chemin.startswith('/'):
        chemin = '/' + chemin
    interne = chemin.strip('/')
    if not interne:
        return ['index.html']
    return [f"{interne}/index.html", f"{interne}.html"]


for url in attendues:
    nom = (url.strip('/').upper() or 'ACCUEIL')
    fichier = None
    for c in candidats(url):
        if os.path.isfile(os.path.join(dossier, c)):
            fichier = c
            break

    if not fichier:
        essais = ', '.join(candidats(url))
        print(f"  {url:28s} ABSENTE")
        mw.probleme(r, nom, 'page-manquante',
                    f"Page attendue {url} absente du build statique.",
                    "Verifier que cette route existe et qu'elle est bien prerendue. "
                    "Si la page n'existe plus, retirer son URL de la liste \"pages\" "
                    "dans mw-config.json.",
                    trouve="aucun fichier (" + essais + ")",
                    attendu=candidats(url)[0])
        continue

    s = open(os.path.join(dossier, fichier), encoding='utf-8', errors='replace').read()
    noindex = mw.est_noindex(s)
    contenu = len(mw.contenu_principal(s))
    canon = mw.canonique(s)
    attendue_url = mw.url_attendue(fichier, domaine) if domaine else None
    soucis = []

    if noindex:
        # "pages" recense les pages publiques destinees a l'indexation :
        # une directive noindex y est une contradiction, pas un detail.
        message = (f"Page {url} declaree comme page publique indexable dans "
                   "mw-config.json, mais elle contient une directive noindex.")
        action = ("Retirer la directive noindex, ou retirer cette URL de la "
                  "liste \"pages\" dans mw-config.json si la page doit rester "
                  "hors index.")
        if mode == 'strict':
            print(f"  {url:28s} PROBLEME : noindex sur une page declaree indexable")
            mw.probleme(r, nom, 'noindex-declare', message, action,
                        trouve="noindex", attendu="page indexable")
        else:
            print(f"  {url:28s} avertissement : noindex sur une page declaree indexable")
            mw.avertir(r, nom, 'noindex-declare', message, action,
                       trouve="noindex", attendu="page indexable")
        continue

    if contenu < 250:
        soucis.append('contenu')
        mw.probleme(r, nom, 'html-vide',
                    f"Page attendue {url} : le HTML initial est presque vide. "
                    f"{contenu} caracteres de contenu principal detectes.",
                    "Verifier le prerendu de cette route.",
                    f"{contenu} caracteres", "250+ caracteres")

    if attendue_url and mw.normaliser(canon or '') != mw.normaliser(attendue_url):
        soucis.append('canonical')
        mw.probleme(r, nom, 'canonical',
                    f"Page attendue {url} : la canonical ne correspond pas a son URL finale.",
                    f"Faire pointer la canonical vers {attendue_url}.",
                    canon or "(absente)", attendue_url)

    if domaine and sitemap:
        if mw.echapper_xml(attendue_url) not in sitemap:
            soucis.append('sitemap')
            mw.probleme(r, nom, 'sitemap',
                        f"Page attendue {url} : absente du sitemap.xml alors "
                        "qu'elle doit etre indexee.",
                        "Corriger sa canonical : le sitemap ne retient que les "
                        "pages canoniques d'elles-memes sur le domaine final.",
                        "absente du sitemap", attendue_url)

    print(f"  {url:28s} {'OK' if not soucis else 'PROBLEME : ' + ', '.join(soucis)}"
          f"   ({fichier}, {contenu} car.)")

if r['errors'] and mode == 'strict':
    r['status_global'] = 'blocked'
mw.sauver(r)
sys.exit(0)
