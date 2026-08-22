"""Determine ou vivent les sauvegardes, de facon identique au deploiement
et a la restauration.

Regle absolue : les sauvegardes ne doivent jamais se trouver a l'interieur du
dossier publie. Sinon elles seraient telechargeables depuis le web, et surtout
effacees par le miroir avec suppression du deploiement suivant.

  resolve_backup_path.py <chemin_distant> [<backup_path_configure>]
"""
import os, posixpath, sys
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

# ---------------------------------------------------------------------
# SONDE TEMPORAIRE : ou le compte FTP autorise-t-il l ecriture ?
# (retiree des que le bon emplacement par defaut est etabli)
# ---------------------------------------------------------------------
def _sonde():
    import subprocess, tempfile
    connect = os.environ.get('CONNECT_FILE', '')
    if not connect or not os.path.isfile(connect):
        print("::warning title=MW sonde::CONNECT_FILE absent")
        return
    base = os.environ.get('RUNNER_TEMP', tempfile.gettempdir())
    parent = posixpath.dirname(remote)
    essais = [
        ('A_frere_du_site', posixpath.join(parent, '.mw-probe') if parent else '.mw-probe'),
        ('B_racine_compte', '.mw-probe'),
        ('C_backups_racine', 'backups/.mw-probe'),
        ('D_dans_le_site', posixpath.join(remote, '.mw-probe') if remote else '.mw-probe'),
    ]
    resultats = []
    for nom, chemin in essais:
        f = os.path.join(base, 'probe-%s.txt' % nom)
        with open(f, 'w', encoding='utf-8') as g:
            g.write(open(connect, encoding='utf-8').read())
            g.write('mkdir -p "%s"\n' % chemin)
            g.write('quit\n')
        c = subprocess.run(['lftp', '-f', f], capture_output=True, text=True)
        ok = (c.returncode == 0)
        resultats.append('%s=%s' % (nom, 'ok' if ok else 'echec'))
        if ok:
            f2 = os.path.join(base, 'probe-rm-%s.txt' % nom)
            with open(f2, 'w', encoding='utf-8') as g:
                g.write(open(connect, encoding='utf-8').read())
                g.write('rmdir "%s"\n' % chemin)
                g.write('quit\n')
            subprocess.run(['lftp', '-f', f2], capture_output=True, text=True)
    print("::warning title=MW sonde::" + " | ".join(resultats))


try:
    _sonde()
except Exception as exc:
    print("::warning title=MW sonde::erreur de sonde: %s" % exc)

print(f"\nSauvegardes ({origine}) : {candidat}")
r['backupPath'] = candidat
mw.sauver(r)
publier(candidat, True, suppression)
