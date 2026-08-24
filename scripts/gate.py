"""Expose l'etat bloque/non bloque du rapport aux etapes suivantes du workflow.

Quand la publication est bloquee, la raison est aussi ecrite sous forme
d'annotation GitHub (::error::). Elle reste ainsi visible directement sur la
page du run, sans avoir a ouvrir les journaux ni le rapport detaille.
"""
import os
import mw_common as mw

r = mw.charger()
bloque = r.get('status_global') == 'blocked'
env = os.environ.get('GITHUB_ENV')
if env:
    open(env, 'a', encoding='utf-8').write(f"MW_BLOCKED={'true' if bloque else 'false'}\n")

if bloque:
    # GitHub n'affiche que dix annotations par etape : tous les problemes sont
    # donc rassembles dans une seule annotation, une ligne par probleme.
    lignes = []
    for e in r.get('errors', []):
        t = f"{e.get('page', '')} / {e.get('type', '')} : {e.get('message', '')}"
        if e.get('found'):
            t += f" [trouve: {e['found']}]"
        if e.get('expected'):
            t += f" [attendu: {e['expected']}]"
        lignes.append(t.replace('\n', ' '))
    if lignes:
        corps = '%0A'.join(f"- {l}" for l in lignes)
        print(f"::error title=MW Agency - {len(lignes)} probleme(s)::{corps}")

print("PUBLICATION BLOQUEE - les etapes suivantes sont ignorees" if bloque
      else "Poursuite du deploiement")
