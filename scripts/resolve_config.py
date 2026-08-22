"""Determine la configuration effective du site.

Priorite : mw-config.json  >  parametres historiques du workflow.

Ce script ne s'interrompt JAMAIS brutalement sur une configuration invalide :
il enregistre le probleme dans mw-report.json, publie des sorties sures, et
laisse le workflow produire le rapport et l'email avant de virer au rouge.
"""
import json, os, re, sys
import mw_common as mw

racine = sys.argv[1] if len(sys.argv) > 1 else '.'

# Parametres historiques passes par le workflow (compatibilite anciens depots)
h_mode     = os.environ.get('IN_MODE', 'auto')
h_seo      = os.environ.get('IN_SEO_CHECK', 'rapport')
h_langue   = os.environ.get('IN_SEO_LANGUE', 'fr')
h_local    = os.environ.get('IN_SEO_LOCAL', 'true') == 'true'
h_site_url = os.environ.get('SITE_URL', '').strip()

r = mw.charger()
erreurs_config = []


def refuser(message, action, trouve=None, attendu=None):
    erreurs_config.append(message)
    mw.probleme(r, 'CONFIGURATION', 'configuration', message, action, trouve, attendu,
                categorie='lovable')


def publier(valeurs):
    """Sorties toujours definies : le rapport et la notification en dependent."""
    sortie = os.environ.get('GITHUB_OUTPUT')
    if sortie:
        with open(sortie, 'a', encoding='utf-8') as f:
            for k, v in valeurs.items():
                f.write(f"{k}={v}\n")
    for k, v in valeurs.items():
        print(f"  {k:18s}: {v}")


def sortir(valeurs, statut_global=None):
    if statut_global:
        r['status_global'] = statut_global
    mw.sauver(r)
    print("Configuration retenue")
    publier(valeurs)
    if erreurs_config:
        print()
        print("CONFIGURATION INVALIDE - la publication sera bloquee.")
        for e in erreurs_config:
            print("  -", e)
    sys.exit(0)


# Sorties de repli, utilisees si la configuration est inexploitable.
# notify=true : une erreur de configuration bloque tout, elle merite un email.
REPLI = {'source': 'configuration invalide', 'domain': '', 'language': 'fr',
         'status': 'chantier', 'localBusiness': 'true', 'backup_path': '',
         'deploy_mode': 'manuel', 'seo_mode': 'strict', 'notify': 'true'}

# ------------------------------------------------------------ lecture
chemin = os.path.join(racine, 'mw-config.json')
cfg, source = {}, 'parametres historiques du workflow'

if os.path.isfile(chemin):
    try:
        cfg = json.load(open(chemin, encoding='utf-8'))
        if not isinstance(cfg, dict):
            raise ValueError("le fichier ne contient pas un objet JSON")
        source = 'mw-config.json'
    except Exception as e:
        refuser(f"mw-config.json est illisible ou mal forme ({e}).",
                "Corriger la syntaxe de mw-config.json : il doit contenir un objet "
                "JSON valide avec les cles domain, language, status et localBusiness.",
                trouve=str(e), attendu="objet JSON valide")
        sortir(REPLI, 'blocked')

domaine     = (cfg.get('domain') or h_site_url or '').strip().rstrip('/')
langue      = (cfg.get('language') or h_langue).strip() or 'fr'
local       = cfg.get('localBusiness', h_local)
# backup_path n'a qu'une seule source de verite : mw-config.json.
backup_path = (cfg.get('backup_path') or '').strip()

# ------------------------------------------------------------ statut
if source == 'mw-config.json':
    statut = (cfg.get('status') or 'chantier').strip().lower()
    if statut not in ('chantier', 'livre'):
        refuser(f"Le statut \"{statut}\" est invalide.",
                "Le champ status de mw-config.json doit valoir \"chantier\" ou \"livre\".",
                trouve=statut, attendu="chantier ou livre")
        sortir(dict(REPLI, domain=domaine, language=langue,
                    backup_path=backup_path), 'blocked')
    mode = 'auto' if statut == 'chantier' else 'manuel'
    seo  = 'rapport' if statut == 'chantier' else 'strict'
    notifier = (statut == 'livre')
else:
    statut = 'chantier' if h_mode != 'manuel' else 'livre'
    mode, seo, notifier = h_mode, h_seo, (h_mode == 'manuel')

r.update(domain=domaine, language=langue, status=statut, localBusiness=bool(local))

valeurs = {
    'source': source, 'domain': domaine, 'language': langue,
    'status': statut, 'localBusiness': 'true' if local else 'false',
    'backup_path': backup_path,
    'deploy_mode': mode, 'seo_mode': seo,
    'notify': 'true' if notifier else 'false',
}

# ------------------------------------------------------------ domaine
if domaine and not re.match(r'(?i)^https?://[^/\s]+$', domaine):
    refuser(f"Le domaine \"{domaine}\" n'est pas une adresse valide.",
            "Renseigner un domaine de la forme https://client.ch dans mw-config.json.",
            trouve=domaine, attendu="https://client.ch")
    sortir(dict(valeurs, notify='true'), 'blocked')

# Le domaine alimente les canonical, le sitemap, robots.txt, og:url et le
# controle de production : un site livre ne peut pas s'en passer.
if statut == 'livre':
    souci = None
    if not domaine:
        souci = "aucun domaine n'est configure"
    elif not domaine.lower().startswith('https://'):
        souci = f"le domaine \"{domaine}\" n'est pas en HTTPS"
    else:
        mauvais = mw.hote_interdit(domaine)
        if mauvais:
            souci = f"le domaine \"{domaine}\" est une adresse de developpement ({mauvais})"

    if souci:
        refuser(f"Site declare livre mais {souci}.",
                "Renseigner le domaine final dans mw-config.json. Dire dans "
                "Lovable : \"Le domaine final est https://client.ch\".",
                trouve=domaine or "(vide)", attendu="https://domaine-final.ch")
        sortir(dict(valeurs, notify='true'), 'blocked')

if not domaine:
    mw.avertir(r, 'CONFIGURATION', 'domaine',
               "Aucun domaine configure : sitemap, canonical et controle de "
               "production seront limites.",
               "Renseigner \"domain\" dans mw-config.json.")

sortir(valeurs)
