"""Sitemap de production : uniquement des pages reellement indexables.

Ne liste pas betement tous les .html. Une page n'entre dans le sitemap que si
elle est indexable, canonique d'elle-meme, et sur le domaine final.
Pas de lastmod ni de priority inventes : mieux vaut rien qu'une donnee fausse.
"""
import os, re, sys, glob
import mw_common as mw

dossier = sys.argv[1]
domaine = (sys.argv[2] or '').rstrip('/')

r = mw.charger()

if not domaine:
    print("Aucun domaine configure : sitemap non genere.")
    mw.avertir(r, 'SITEMAP', 'sitemap', "Sitemap non genere : domaine absent.",
               "Renseigner \"domain\" dans mw-config.json.")
    mw.sauver(r); sys.exit(0)

pages = mw.pages_html(dossier)
for v in mw.fichiers_verification(dossier):
    print(f"Fichier de verification Search Console ignore (deploye tel quel) : {v}")
retenues, ecartees = [], []
vues = set()

for chemin in pages:
    rel = os.path.relpath(chemin, dossier).replace(os.sep, '/')
    s = open(chemin, encoding='utf-8', errors='replace').read()
    attendue = mw.url_attendue(rel, domaine)
    classe = mw.classe_page(rel)

    if classe == 'technique':
        ecartees.append((rel, "page technique")); continue
    if mw.est_noindex(s):
        ecartees.append((rel, "noindex")); continue

    canon = mw.canonique(s)
    if not canon:
        ecartees.append((rel, "aucune canonical")); continue
    if not re.match(r'(?i)^https?://', canon):
        ecartees.append((rel, "canonical relative")); continue
    if mw.hote_interdit(canon):
        ecartees.append((rel, "canonical sur un domaine de developpement")); continue

    hote_domaine = re.match(r'(?i)^https?://([^/]+)', domaine).group(1).lower()
    hote_canon = re.match(r'(?i)^https?://([^/]+)', canon).group(1).lower()
    if hote_canon != hote_domaine:
        ecartees.append((rel, f"canonical sur un autre domaine ({hote_canon})")); continue

    if mw.normaliser(canon) != mw.normaliser(attendue):
        ecartees.append((rel, "canonical pointant vers une autre page")); continue

    cle = mw.normaliser(canon)
    if cle in vues:
        ecartees.append((rel, "doublon")); continue
    vues.add(cle)
    retenues.append(attendue)

lignes = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in sorted(retenues):
    lignes += ['  <url>', f'    <loc>{mw.echapper_xml(u)}</loc>', '  </url>']
lignes.append('</urlset>')

open(os.path.join(dossier, 'sitemap.xml'), 'w', encoding='utf-8').write(
    '\n'.join(lignes) + '\n')

print(f"sitemap.xml : {len(retenues)} page(s) retenue(s)")
for u in sorted(retenues):
    print("   +", u)
if ecartees:
    print(f"{len(ecartees)} page(s) ecartee(s) :")
    for rel, raison in ecartees:
        print(f"   - {rel} ({raison})")

if not retenues:
    mw.probleme(r, 'SITEMAP', 'sitemap',
                "Aucune page indexable n'a pu entrer dans le sitemap.",
                "Verifier les canonical : chaque page publique doit porter une "
                "canonical absolue vers sa propre URL sur le domaine final.")

# ---------------------------------------------------------------- robots.txt
chemin_robots = os.path.join(dossier, 'robots.txt')
ligne = f"Sitemap: {domaine}/sitemap.xml"

if os.path.isfile(chemin_robots):
    contenu = open(chemin_robots, encoding='utf-8', errors='replace').read()
    existante = re.search(r'(?im)^\s*sitemap\s*:\s*(\S+)\s*$', contenu)
    if existante:
        if mw.normaliser(existante.group(1)) != mw.normaliser(f"{domaine}/sitemap.xml"):
            contenu = re.sub(r'(?im)^\s*sitemap\s*:\s*\S+\s*$', ligne, contenu)
            open(chemin_robots, 'w', encoding='utf-8').write(contenu)
            print("robots.txt : reference au sitemap corrigee vers le domaine final")
        else:
            print("robots.txt : reference au sitemap deja correcte")
    else:
        if not contenu.endswith('\n'):
            contenu += '\n'
        open(chemin_robots, 'w', encoding='utf-8').write(contenu + '\n' + ligne + '\n')
        print("robots.txt : reference au sitemap ajoutee (fichier existant conserve)")
else:
    open(chemin_robots, 'w', encoding='utf-8').write(
        "User-agent: *\nAllow: /\n\n" + ligne + "\n")
    print("robots.txt cree (standard minimal)")

mw.sauver(r)
