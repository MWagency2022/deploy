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
    for e in r.get('errors', []):
        texte = f"{e.get('page', '')} / {e.get('type', '')} : {e.get('message', '')}"
        trouve = e.get('found')
        attendu = e.get('expected')
        if trouve:
            texte += f" [trouve: {trouve}]"
        if attendu:
            texte += f" [attendu: {attendu}]"
        print("::error title=MW Agency::" + texte.replace('\n', ' '))

print("PUBLICATION BLOQUEE - les etapes suivantes sont ignorees" if bloque
      else "Poursuite du deploiement")
