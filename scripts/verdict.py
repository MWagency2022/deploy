"""Derniere etape : fait echouer le workflow si necessaire, une fois le
rapport produit et l'email envoye."""
import sys
import mw_common as mw

r = mw.charger()
operation = r.get('operation', 'deploiement')

if operation == 'restauration':
    revert = r.get('revert', 'none')
    if revert == 'failed':
        print("Restauration ET retour arriere en echec : intervention technique requise.")
        sys.exit(1)
    if revert == 'done':
        print("Restauration annulee : la sauvegarde demandee n'etait pas fonctionnelle.")
        sys.exit(1)
    if r.get('status_global') == 'blocked':
        print("Restauration bloquee : aucun fichier n'a ete modifie.")
        sys.exit(1)
    if r.get('restore') == 'failed':
        print("Le transfert de restauration a echoue.")
        sys.exit(1)
    if r.get('restore') == 'ok' and r.get('productionCheck') != 'ok':
        print("Version restauree non fonctionnelle.")
        sys.exit(1)
    if r.get('restore') == 'ok':
        print("Restauration reussie.")
    else:
        print("Aucune restauration demandee.")
    sys.exit(0)

rollback = r.get('rollback', 'none')
if rollback == 'failed':
    print("La restauration automatique a echoue : intervention technique requise.")
    sys.exit(1)
if rollback in ('done', 'impossible'):
    print("Le workflow est marque en echec : voir le resume ci-dessus.")
    sys.exit(1)
if r.get('status_global') == 'blocked':
    print("Publication bloquee : voir le resume ci-dessus.")
    sys.exit(1)
if not r.get('published'):
    print("Aucune publication demandee : rien a signaler.")
    sys.exit(0)
print("Publication reussie.")
sys.exit(0)
