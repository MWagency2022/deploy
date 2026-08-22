"""Enregistre l'issue d'une etape dans mw-report.json."""
import argparse, sys
import mw_common as mw

p = argparse.ArgumentParser()
p.add_argument('champ'); p.add_argument('valeur')
p.add_argument('--page', default='SYSTEME'); p.add_argument('--type', default='etape')
p.add_argument('--message'); p.add_argument('--action', default='')
p.add_argument('--trouve', default=None); p.add_argument('--attendu', default=None)
p.add_argument('--bloquant', action='store_true')
p.add_argument('--avertissement', action='store_true')
p.add_argument('--categorie', default=None, choices=['lovable', 'technique'])
a = p.parse_args()

r = mw.charger()
r[a.champ] = a.valeur
if a.message:
    if a.avertissement:
        mw.avertir(r, a.page, a.type, a.message, a.action, a.trouve, a.attendu, a.categorie)
    else:
        mw.probleme(r, a.page, a.type, a.message, a.action, a.trouve, a.attendu, a.categorie)
if a.bloquant:
    r['status_global'] = 'blocked'
mw.sauver(r)
print(f"{a.champ} = {a.valeur}" + (" (bloquant)" if a.bloquant else ""))
