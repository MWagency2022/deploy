"""Determine ou vivent les sauvegardes, de facon identique au deploiement
et a la restauration.

Regle absolue : les sauvegardes ne doivent jamais se trouver a l'interieur du
dossier publie. Sinon elles seraient telechargeables depuis le web, et surtout
effacees par le miroir avec suppression du deploiement suivant.

  resolve_backup_path.py <chemin_distant> [<backup_path_configure>]
"""
import os, posixpath, subprocess, sys
import mw_common as mw

distant   = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
configure = (sys.argv[2] if len(sys.argv) > 2 else '').strip()

r = mw.charger()
remote = distant.rstrip('/')
racine_du_compte = remote in ('', '.', './', '/')


def normaliser(p):
    p = p.strip().rstrip('/')
    return posixpath.normpath(p) if p else '.'


def est_dans(candidat, base):
    """Le candidat est-il a l'interieur de la base (ou egal a elle) ?"""
    c, b = normaliser(candidat), normaliser(base)
    if b in ('.', '/'):
        # Depuis la racine du compte, tout chemin relatif qui ne remonte pas
        # est a l'interieur. Un chemin absolu ou remontant en sort.
        if c.startswith('/'):
            return False
        return not c.startswith('..')
    return c == b or c.startswith(b + '/')


def publier(root, sur, suppression):
    env = os.environ.get('GITHUB_ENV')
    lignes = {'BACKUP_ROOT': root, 'BACKUP_SAFE': '1' if sur else '0',
              'MIRROR_DELETE': suppression}
    if env:
        with open(env, 'a', encoding='utf-8') as f:
            for k, v in lignes.items():
                f.write(f"{k}={v}\n")
    sortie = os.environ.get('GITHUB_OUTPUT')
    if sortie:
        with open(sortie, 'a', encoding='utf-8') as f:
            for k, v in lignes.items():
                f.write(f"{k.lower()}={v}\n")
    for k, v in lignes.items():
        print(f"  {k:14s}: {v if v else '(vide)'}")


def bloquer(message, action, trouve=None, attendu=None):
    print("\nPUBLICATION BLOQUEE")
    print(message)
    mw.probleme(r, 'SAUVEGARDE', 'backup', message, action, trouve, attendu,
                categorie='technique')
    r['status_global'] = 'blocked'
    r['backup'] = 'failed'
    mw.sauver(r)
    publier('', False, '')
    sys.exit(0)


print(f"Chemin distant : {remote or '(racine du compte)'}")
print(f"backup_path    : {configure or '(automatique)'}")

# --- suppression des fichiers obsoletes -------------------------------
# A la racine du compte, un miroir avec suppression emporterait les autres
# sites, les boites mail et les sauvegardes.
suppression = '' if racine_du_compte else '--delete'

# --- choix du chemin ---------------------------------------------------
if configure:
    candidat = configure.rstrip('/')
    origine = 'backup_path'
else:
    if racine_du_compte:
        bloquer("Le chemin distant designe la racine du compte FTP et aucun "
                "backup_path n'est configure : impossible de placer les "
                "sauvegardes hors du site publie.",
                "Renseigner \"backup_path\" dans mw-config.json avec un dossier "
                "situe hors du site (par exemple \"../sauvegardes\"), ou faire "
                "pointer SFTP_REMOTE_PATH sur un sous-dossier dedie.",
                trouve=remote or "(racine)", attendu="un dossier dedie")
    candidat = f"backups/{posixpath.basename(normaliser(remote))}"
    origine = 'automatique'

# --- verification de securite ------------------------------------------
if normaliser(candidat) in ('.', '/'):
    bloquer(f"Le chemin de sauvegarde ({origine}) designe la racine : "
            "les sauvegardes y seraient melangees au site.",
            "Renseigner un sous-dossier dedie dans \"backup_path\".",
            trouve=candidat, attendu="un dossier dedie")

if est_dans(candidat, remote):
    bloquer(f"Le chemin de sauvegarde \"{candidat}\" ({origine}) se trouve a "
            "l'interieur du dossier publie. Les sauvegardes y seraient "
            "accessibles depuis le web et effacees au deploiement suivant.",
            "Renseigner \"backup_path\" dans mw-config.json avec un dossier "
            "situe hors du site publie.",
            trouve=candidat, attendu=f"un dossier hors de {remote or 'la racine'}")

# --- creation du dossier des sauvegardes -------------------------------
# Certains serveurs SFTP refusent de creer plusieurs niveaux d'un seul coup.
# Le dossier est donc construit segment par segment, avant tout envoi.

def _lftp(lignes, tolerant):
    connect = os.environ.get('CONNECT_FILE', '')
    if not connect or not os.path.isfile(connect):
        return None                      # hors deploiement : rien a preparer
    base = os.environ.get('RUNNER_TEMP') or '.'
    _lftp.n += 1
    f = os.path.join(base, f'mw-prep-{_lftp.n}.txt')
    with open(f, 'w', encoding='utf-8') as g:
        g.write(open(connect, encoding='utf-8').read())
        if tolerant:
            g.write('set cmd:fail-exit no\n')   # un dossier deja present n'est pas une erreur
        for l in lignes:
            g.write(l + '\n')
        g.write('quit\n')
    return subprocess.run(['lftp', '-f', f], capture_output=True, text=True).returncode


_lftp.n = 0


def preparer(chemin):
    """Cree le dossier des sauvegardes niveau par niveau. Best effort :
    un echec ici n'est pas un verdict, c'est l'etape de sauvegarde qui
    tranche selon le statut du site."""
    p = normaliser(chemin)
    absolu = p.startswith('/')
    lignes, courant = [], ''
    for seg in [x for x in p.split('/') if x not in ('', '.')]:
        courant = f'{courant}/{seg}' if courant else (f'/{seg}' if absolu else seg)
        lignes.append(f'mkdir "{courant}"')
    if not lignes:
        return None
    if _lftp(lignes, True) is None:
        return None
    return _lftp([f'cd "{p}"'], False) == 0

print(f"\nSauvegardes ({origine}) : {candidat}")
r['backupPath'] = candidat

etat = preparer(candidat)
if etat is True:
    print("Dossier des sauvegardes pret.")
elif etat is False:
    print("Le dossier des sauvegardes n'a pas pu etre cree sur le serveur.")
    mw.info(r, "Le dossier des sauvegardes n'a pas pu etre cree sur le serveur.")

# --- DIAGNOSTIC TEMPORAIRE --------------------------------------------
def _essai(cmds):
    import tempfile
    connect = os.environ.get('CONNECT_FILE', '')
    base = os.environ.get('RUNNER_TEMP') or tempfile.gettempdir()
    _essai.n = getattr(_essai, 'n', 0) + 1
    f = os.path.join(base, 'e%d.txt' % _essai.n)
    with open(f, 'w', encoding='utf-8') as g:
        g.write(open(connect, encoding='utf-8').read())
        for c in cmds:
            g.write(c + '\n')
        g.write('quit\n')
    c = subprocess.run(['lftp', '-f', f], capture_output=True, text=True)
    return c.returncode, (c.stdout + ' ' + c.stderr).strip().replace('\n', ' ')


def _diag():
    connect = os.environ.get('CONNECT_FILE', '')
    if not connect or not os.path.isfile(connect):
        return
    lignes = []
    for etiquette, cmds in [
        ('pwd', ['pwd']),
        ('mkdir_backups', ['mkdir "backups"']),
        ('cd_backups', ['cd "backups"']),
        ('mkdir_niveau2', ['mkdir "backups/testmwagency.ch"']),
        ('cd_niveau2', ['cd "backups/testmwagency.ch"']),
        ('mkdir_frere', ['mkdir "sites/.mw-backups"']),
        ('cd_frere', ['cd "sites/.mw-backups"']),
    ]:
        code, txt = _essai(cmds)
        lignes.append('%s=%s(%s)' % (etiquette, code, txt[:90]))
    print('::warning title=MW diag::' + ' || '.join(lignes)[:900])


try:
    _diag()
except Exception as exc:
    print('::warning title=MW diag::erreur %s' % exc)

mw.sauver(r)
publier(candidat, True, suppression)
