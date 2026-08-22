"""Identite du site distant : ne jamais ecrire dans le dossier d'un autre client.

  ecrire   <build_dir> <domaine> <depot>
  verifier --connexion ok|erreur --parent ok|erreur
           --dossier existe|absent|illisible --vide oui|non
           --marqueur <chemin|aucun|erreur> --domaine X --depot Y [--adopter]

Deux regles de fond :

1. Une erreur de reseau, de droits ou de listing n'est JAMAIS interpretee comme
   un dossier neuf. L'absence doit etre PROUVEE : le dossier parent est lisible
   et ne contient pas le nom cible.
2. L'adoption ne peut pas passer outre un marqueur appartenant a un autre site.
   Transferer volontairement la propriete d'un dossier releve d'une procedure
   administrative distincte, pas d'une case a cocher.
"""
import argparse, json, os, sys
import mw_common as mw


def ecrire(dossier, domaine, depot):
    marqueur = {"domain": domaine, "repository": depot}
    with open(os.path.join(dossier, '.mw-site.json'), 'w', encoding='utf-8') as f:
        json.dump(marqueur, f, ensure_ascii=False, indent=2)
    print(f"Marqueur ecrit : {domaine} / {depot}")


def bloquer(r, message, action, trouve=None, attendu=None, etat='failed'):
    print("\nPUBLICATION REFUSEE")
    print(message)
    print("Aucun fichier n'a ete modifie.")
    mw.probleme(r, 'FTP', 'identite', message, action, trouve, attendu)
    r['identity'] = etat
    r['status_global'] = 'blocked'
    mw.sauver(r)


def verifier(a):
    r = mw.charger()

    # --- 1. la connexion au compte ---------------------------------------
    if a.connexion != 'ok':
        bloquer(r,
                "Impossible de se connecter au serveur ou de lire le compte FTP.",
                "Verifier SFTP_HOST, SFTP_USERNAME, SFTP_PASSWORD, SFTP_PORT et "
                "le protocole. Tant que le serveur n'a pas repondu, aucune "
                "ecriture n'est tentee.",
                etat='erreur-connexion')
        return

    # --- 2. le dossier parent doit etre lisible ---------------------------
    # C'est lui qui prouve l'absence : sans cette preuve, on ne conclut rien.
    if a.parent != 'ok':
        bloquer(r,
                "Le dossier parent du chemin distant n'a pas pu etre lu. "
                "Impossible de determiner si le dossier cible existe.",
                "Verifier SFTP_REMOTE_PATH et les droits de lecture du compte "
                "FTP sur ce chemin, puis relancer.",
                etat='erreur-parent')
        return

    # --- 3. dossier present dans le parent mais illisible ------------------
    if a.dossier == 'illisible':
        bloquer(r,
                "Le dossier distant existe mais n'a pas pu etre lu. Cette "
                "situation n'est pas traitee comme un nouveau site.",
                "Verifier les droits de lecture sur le dossier distant, "
                "puis relancer la publication.",
                etat='erreur-lecture')
        return

    # --- 4. absence prouvee : le parent ne contient pas le nom cible -------
    if a.dossier == 'absent':
        print("Le dossier distant n'existe pas dans son parent : premier deploiement.")
        print("Le marqueur sera ecrit avec les fichiers du site.")
        r['identity'] = 'nouveau'
        mw.sauver(r)
        return

    # --- 5. marqueur present mais illisible -------------------------------
    if a.marqueur == 'erreur':
        bloquer(r,
                "Le marqueur .mw-site.json existe sur le serveur mais n'a pas pu "
                "etre lu. Cette situation n'est pas traitee comme un nouveau site.",
                "Verifier les droits de lecture sur le dossier distant, puis "
                "relancer la publication.",
                etat='erreur-lecture')
        return

    # --- 6. dossier present, sans marqueur --------------------------------
    if a.marqueur == 'aucun':
        if a.vide == 'oui':
            print("Dossier distant vide et sans marqueur : premier deploiement autorise.")
            r['identity'] = 'nouveau'
            mw.sauver(r)
            return
        if a.adopter:
            print("Dossier distant non vide, sans marqueur.")
            print("Adoption explicite demandee : le dossier sera adopte par ce depot.")
            mw.avertir(r, 'FTP', 'identite',
                       "Dossier distant non vide adopte alors qu'il ne portait aucun marqueur.",
                       "Verifier que ce dossier correspond bien a ce site.")
            r['identity'] = 'adopte'
            mw.sauver(r)
            return
        bloquer(r,
                "Le dossier distant contient deja des fichiers mais ne porte aucun "
                "marqueur MW Agency. Impossible de garantir qu'il appartient bien "
                "a ce site.",
                "Verifier SFTP_REMOTE_PATH. S'il s'agit reellement du bon dossier, "
                "relancer via Actions > Deploiement > Run workflow en cochant "
                "\"adopter_dossier_distant\".",
                trouve="dossier non vide, sans marqueur",
                attendu=f"{a.domaine} ({a.depot})",
                etat='non-marque')
        return

    # --- 7. marqueur present : comparaison --------------------------------
    try:
        distant = json.load(open(a.marqueur, encoding='utf-8'))
    except Exception as e:
        bloquer(r,
                f"Le marqueur .mw-site.json du serveur est illisible ou mal forme ({e}).",
                "Inspecter le dossier distant avant de publier.",
                etat='erreur-lecture')
        return

    dom_distant = distant.get('domain') or ''
    dep_distant = (distant.get('repository') or '').strip()

    conforme = (mw.normaliser(dom_distant) == mw.normaliser(a.domaine)
                and dep_distant.lower() == a.depot.strip().lower())

    if conforme:
        print(f"Marqueur distant conforme : {dom_distant} / {dep_distant}")
        r['identity'] = 'ok'
        mw.sauver(r)
        return

    # Conflit de marqueur : l'adoption ordinaire ne peut PAS passer outre.
    if a.adopter:
        print("L'option d'adoption ne s'applique pas a un dossier deja marque "
              "au nom d'un autre site.")
    bloquer(r,
            f"Ce dossier distant appartient a {dom_distant} ({dep_distant}), "
            f"pas a ce site.",
            "Corriger SFTP_REMOTE_PATH dans les secrets de ce depot. Un transfert "
            "volontaire de propriete entre deux projets ne passe pas par l'option "
            "d'adoption : il faut retirer ou modifier le fichier .mw-site.json "
            "sur le serveur, deliberement.",
            trouve=dom_distant, attendu=a.domaine, etat='conflit')


def verifier_sauvegarde(dossier, domaine, depot, nom_sauvegarde):
    """Une sauvegarde ne peut etre remise en ligne que si elle appartient
    bien a ce site. Sans cette verification, une erreur de chemin pourrait
    installer le site d'un client chez un autre."""
    r = mw.charger()
    marqueur = os.path.join(dossier, '.mw-site.json')

    def refuser(message, action, trouve=None):
        print("\nRESTAURATION REFUSEE")
        print(message)
        print("Aucun fichier n'a ete modifie.")
        mw.probleme(r, 'SAUVEGARDE', 'identite', message, action, trouve, domaine)
        r['backupIdentity'] = 'refuse'
        r['status_global'] = 'blocked'
        mw.sauver(r)

    if not os.path.isfile(marqueur):
        refuser(f"La sauvegarde {nom_sauvegarde} ne contient pas de marqueur "
                ".mw-site.json : impossible de verifier a quel site elle appartient.",
                "Cette sauvegarde est probablement anterieure a la mise en place "
                "du marqueur. Verifier son contenu manuellement avant de la "
                "remettre en ligne.",
                trouve="aucun marqueur")
        return

    try:
        contenu = json.load(open(marqueur, encoding='utf-8'))
    except Exception as e:
        refuser(f"Le marqueur de la sauvegarde {nom_sauvegarde} est illisible ({e}).",
                "Verifier le contenu de cette sauvegarde avant de la restaurer.",
                trouve="marqueur illisible")
        return

    dom = contenu.get('domain') or ''
    dep = (contenu.get('repository') or '').strip()

    if (mw.normaliser(dom) != mw.normaliser(domaine)
            or dep.lower() != depot.strip().lower()):
        refuser(f"La sauvegarde {nom_sauvegarde} appartient a {dom} ({dep}), "
                "pas a ce site.",
                "Choisir une sauvegarde de ce site. Une sauvegarde d'un autre "
                "client ne peut pas etre remise en ligne ici.",
                trouve=dom or "(domaine absent)")
        return

    if not os.path.isfile(os.path.join(dossier, 'index.html')):
        refuser(f"La sauvegarde {nom_sauvegarde} ne contient pas de page d'accueil.",
                "Choisir une autre sauvegarde.", trouve="index.html absent")
        return

    fichiers = sum(len(f) for _, _, f in os.walk(dossier))
    print(f"Sauvegarde conforme : {dom} / {dep}, {fichiers} fichiers.")
    r['backupIdentity'] = 'ok'
    mw.sauver(r)


p = argparse.ArgumentParser()
sous = p.add_subparsers(dest='action', required=True)

e = sous.add_parser('ecrire')
e.add_argument('dossier'); e.add_argument('domaine'); e.add_argument('depot')

v = sous.add_parser('verifier')
v.add_argument('--connexion', required=True, choices=['ok', 'erreur'])
v.add_argument('--parent', default='ok', choices=['ok', 'erreur'])
v.add_argument('--dossier', required=True, choices=['existe', 'absent', 'illisible'])
v.add_argument('--vide', default='non', choices=['oui', 'non'])
v.add_argument('--marqueur', required=True)
v.add_argument('--domaine', required=True)
v.add_argument('--depot', required=True)
v.add_argument('--adopter', action='store_true')

vs = sous.add_parser('verifier-sauvegarde')
vs.add_argument('dossier'); vs.add_argument('domaine')
vs.add_argument('depot'); vs.add_argument('nom')

a = p.parse_args()
if a.action == 'ecrire':
    ecrire(a.dossier, a.domaine, a.depot)
elif a.action == 'verifier-sauvegarde':
    verifier_sauvegarde(a.dossier, a.domaine, a.depot, a.nom)
else:
    verifier(a)
sys.exit(0)
