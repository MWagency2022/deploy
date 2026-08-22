"""Expose l'etat bloque/non bloque du rapport aux etapes suivantes du workflow."""
import os
import mw_common as mw

r = mw.charger()
bloque = r.get('status_global') == 'blocked'
env = os.environ.get('GITHUB_ENV')
if env:
    open(env, 'a', encoding='utf-8').write(f"MW_BLOCKED={'true' if bloque else 'false'}\n")
print("PUBLICATION BLOQUEE - les etapes suivantes sont ignorees" if bloque
      else "Poursuite du deploiement")
