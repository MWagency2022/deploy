"""Controle apres transfert : le site est-il reellement fonctionnel ?

Volontairement simple. On ne refait pas un audit SEO : on distingue seulement
"fichiers envoyes" de "site qui repond".
"""
import os, re, sys, time, urllib.request, urllib.error
import mw_common as mw

domaine = (sys.argv[1] or '').rstrip('/')
attend_sitemap = (sys.argv[2] if len(sys.argv) > 2 else 'true') == 'true'

r = mw.charger()

if not domaine:
    print("Aucun domaine configure : controle de production ignore.")
    r['productionCheck'] = 'skipped'
    mw.sauver(r); sys.exit(0)


def demander(url, tentatives=4, attente=10):
    dernier = None
    for i in range(1, tentatives + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'MW-Agency-Deploy/1.0',
                'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=25) as rep:
                corps = rep.read(400000).decode('utf-8', 'replace')
                print(f"  tentative {i} : {rep.status} ({len(corps)} octets lus)")
                return rep.status, corps
        except urllib.error.HTTPError as e:
            dernier = e.code
            print(f"  tentative {i} : HTTP {e.code}")
        except Exception as e:
            dernier = 0
            print(f"  tentative {i} : {type(e).__name__} {e}")
        if i < tentatives:
            time.sleep(attente)
    return dernier or 0, ''


echecs = []

print(f"Page d'accueil : {domaine}/")
code, corps = demander(domaine + '/')
if code not in (200, 301, 302):
    echecs.append(f"la page d'accueil repond {code or 'aucune reponse'}")
elif '<title' not in corps.lower():
    echecs.append("la page d'accueil ne contient pas de balise <title>")
else:
    t = re.search(r'(?is)<title[^>]*>(.*?)</title>', corps)
    print(f"  titre servi : {mw.texte_de(t.group(1)) if t else '(vide)'}")

print(f"\nrobots.txt : {domaine}/robots.txt")
code_r, corps_r = demander(domaine + '/robots.txt', tentatives=2, attente=5)
if code_r != 200:
    echecs.append(f"robots.txt inaccessible ({code_r})")

if attend_sitemap:
    print(f"\nsitemap.xml : {domaine}/sitemap.xml")
    code_s, corps_s = demander(domaine + '/sitemap.xml', tentatives=2, attente=5)
    if code_s != 200:
        echecs.append(f"sitemap.xml inaccessible ({code_s})")
    elif '<urlset' not in corps_s:
        echecs.append("sitemap.xml servi mais ce n'est pas un sitemap valide")
    else:
        hote = re.match(r'(?i)^https?://([^/]+)', domaine).group(1)
        if hote not in corps_s:
            echecs.append("le sitemap en ligne ne contient pas le domaine final")
        else:
            print(f"  sitemap conforme au domaine {hote}")

if echecs:
    print("\nCONTROLE DE PRODUCTION EN ECHEC")
    for e in echecs:
        print("  -", e)
    mw.probleme(r, 'PRODUCTION', 'production',
                "Le site ne repond pas correctement apres le transfert : "
                + " ; ".join(echecs) + ".",
                "Une restauration automatique va etre tentee si une sauvegarde valide existe.")
    r['productionCheck'] = 'failed'
    mw.sauver(r); sys.exit(1)

print("\nSite en ligne et fonctionnel.")
r['productionCheck'] = 'ok'
mw.sauver(r); sys.exit(0)
