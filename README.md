# MW Agency — Moteur de déploiement

Ce dépôt contient le moteur qui met en ligne les sites clients. Aucun site
n'est hébergé ici, aucune valeur propre à un client n'y figure.

Chaque site client appelle ce moteur au lieu d'en posséder sa propre copie :
une correction faite ici profite à tous les sites au déploiement suivant.

## Arborescence

```text
.github/workflows/
    static-deploy.yml      appelé par les dépôts clients — orchestration
    static-restore.yml     restauration manuelle d'une sauvegarde
scripts/
    mw_common.py           analyse HTML, URLs, classement des pages
    resolve_config.py      mw-config.json → configuration effective
    resolve_build_dir.py   détection du dossier de build
    generate_sitemap.py    sitemap.xml + robots.txt
    seo_audit.py           audit du HTML servi aux moteurs
    site_identity.py       marqueur .mw-site.json (anti-écrasement)
    production_check.py    contrôle après transfert
    deployment_report.py   mw-report.json → résumé GitHub + email
    send_notification.py   envoi SMTP
    record.py gate.py verdict.py   petites briques d'orchestration
    htaccess.conf          .htaccess livré par défaut
tests/
    run_tests.py           scénarios exécutés contre les vrais scripts
nouveau-client.sh          branchement guidé d'un nouveau site
clients.md                 inventaire des sites
LOVABLE_WORKSPACE_RULES.md règles à coller une fois dans Lovable
```

Le YAML orchestre, les scripts font le travail. C'est ce qui permet de tester
la logique sans déployer et de corriger sans risquer de casser le YAML.

## mw-config.json — la source de vérité

Placé à la racine du dépôt de chaque site :

```json
{
  "domain": "https://client.ch",
  "language": "fr",
  "status": "chantier",
  "localBusiness": true,
  "backup_path": "",
  "pages": ["/"]
}
```

Rien de sensible ici : ni mot de passe, ni identifiant.

| Champ | Rôle |
|---|---|
| `domain` | Domaine canonique final. Sert au canonical, au sitemap, à robots.txt, à og:url et au contrôle de production |
| `language` | Langue attendue dans `<html lang>` |
| `localBusiness` | Exige un JSON-LD entreprise sur l'accueil |
| `status` | `chantier` ou `livre` — pilote tout le reste |
| `backup_path` | Dossier des sauvegardes. Vide = choisi automatiquement à côté du site |
| `pages` | Pages qui doivent exister après le build. Vide = aucune exigence |

### Le statut pilote tout

| `status` | Déploiement | Audit SEO | Email | Sauvegarde en échec |
|---|---|---|---|---|
| `chantier` | à chaque modification | signale sans bloquer | silencieux | avertissement |
| `livre` | uniquement sur ordre | bloque la publication | après chaque tentative | **bloque la publication** |

Il n'y a plus de `mode` ni de `seo_check` à tenir à jour séparément : dire à
Lovable « passe le site en livré » suffit.

### Compatibilité

Si `mw-config.json` est absent, le moteur retombe sur les entrées historiques
du workflow (`mode`, `seo_check`, `seo_langue`, `seo_local`) et le secret
`SITE_URL`. Les anciens dépôts continuent de fonctionner sans modification ;
la migration peut se faire site par site.

## Ce que fait un déploiement

1. **Décision** — publier ou non, selon le statut et le déclencheur
2. **Build** puis **détection du dossier** (`dist/client`, `dist`, `build`…)
3. **.htaccess**, **marqueur d'identité**, **sitemap et robots.txt**
4. **Audit SEO** — bloquant si le site est livré
5. **Vérification du dossier distant** — refus si le dossier appartient à un autre site
6. **Sauvegarde** de la version en ligne
7. **Transfert** en miroir
8. **Contrôle de production** — le site répond-il vraiment ?
9. **Restauration automatique** si le contrôle échoue
10. **Rapport** — résumé GitHub, artifact, email

Un échec bloquant n'interrompt jamais la production du rapport ni l'envoi de
l'email : le workflow n'est marqué en échec qu'à la toute dernière étape.

La raison d'un blocage s'affiche directement sur la page du run, en haut, sans
avoir à ouvrir les journaux ni le rapport détaillé.

## Publier

Le fichier `publier.txt` du dépôt client vaut ordre de publication : sa
modification déclenche la mise en ligne. Dire dans Lovable « publie le site ».

Deuxième voie, toujours disponible : *Actions → Deploiement → Run workflow*.

En statut `chantier`, tout part automatiquement ; `publier.txt` n'a alors
aucun rôle particulier.

## Audit SEO

Le moteur analyse le **HTML réellement servi aux moteurs**, pas le rendu après
JavaScript : les moteurs de réponse et la plupart des outils d'analyse ne
lisent que le brut.

Le seuil de contenu dépend du rôle de la page, pas d'un chiffre unique :

| Type de page | Exemples | Contenu principal |
|---|---|---|
| principale | accueil, services, pages métier | erreur en dessous de 250 caractères |
| secondaire | contact, mentions, confidentialité | avertissement en dessous de 150 |
| technique | 404, merci, thank-you | aucun seuil |

Le contenu est mesuré dans `<main>` s'il existe, sinon dans `<body>` privé des
`header`, `nav`, `footer` et `aside` — pour ne pas compter le menu comme du
contenu.

Sont également vérifiés : `lang`, `title`, meta description, canonical absolue
et exacte, `og:title`/`og:description`/`og:image`, cohérence `og:url` /
canonical, présence d'un `h1`, validité syntaxique des JSON-LD, JSON-LD
entreprise sur l'accueil, et robots.txt (blocage global détecté).

Sont refusés dans toute URL SEO : `localhost`, `127.0.0.1`, `*.lovable.app`,
`*.vercel.app`, `*.netlify.app`, `example.com`, et tout hôte différent du
domaine configuré.

## Sitemap

N'entrent dans le sitemap que les pages réellement indexables : pas de 404, de
page « merci », de `noindex`, de doublon, ni de page dont la canonical pointe
ailleurs. Chaque `<loc>` utilise exactement le domaine configuré.

Pas de `lastmod` ni de `priority` : le moteur n'a pas d'information fiable sur
la date réelle de modification du contenu, et une donnée inventée vaut moins
que pas de donnée.

## Sauvegardes

Placées à côté du site, jamais dedans : par défaut dans un dossier
`.mw-backups` frère du dossier publié — `sites/.mw-backups/client.ch/` pour un
site déployé dans `sites/client.ch/`. `backup_path` permet d'imposer un autre
emplacement, à condition qu'il soit hors du dossier publié.

Le dossier est créé niveau par niveau : certains serveurs SFTP, dont ceux
d'Infomaniak, refusent de créer plusieurs niveaux d'un seul coup. Un dossier
`backups` à la racine du compte est volontairement évité : chez Infomaniak il
existe déjà et n'est pas accessible en écriture.

Conservation en jours, pas en nombre : tout sur 7 jours, puis une par jour
jusqu'à 60 jours, plus la toute première gardée indéfiniment.

Sur un site **livré** dont la production contient déjà des fichiers, une
sauvegarde impossible bloque la publication : on ne remplace pas le site d'un
client sans filet.

## Ne jamais écraser le site d'un autre client

Le moteur écrit un marqueur `.mw-site.json` à la racine du site déployé :

```json
{ "domain": "https://client.ch", "repository": "MWagency2022/nom-repo" }
```

Avant toute écriture, il lit le marqueur distant. S'il appartient à un autre
site, la publication est refusée **avant le moindre transfert**.

Pour adopter délibérément un dossier existant : *Actions → Deploiement →
Run workflow* en cochant *adopter_dossier_distant*.

## Secrets

### Par client, dans son dépôt

| Secret | Obligatoire |
|---|---|
| `SFTP_HOST` | oui |
| `SFTP_USERNAME` | oui |
| `SFTP_PASSWORD` | oui |
| `SFTP_REMOTE_PATH` | oui — jamais vide ni `.` |
| `SFTP_PORT` | non |
| `SITE_URL` | non — uniquement pour les dépôts sans `mw-config.json` |

### Une seule fois, au niveau de l'organisation

| Secret | Rôle |
|---|---|
| `MW_NOTIFY_HOST` | serveur SMTP |
| `MW_NOTIFY_PORT` | 587 par défaut, 465 pour SSL direct |
| `MW_NOTIFY_USER` | identifiant SMTP |
| `MW_NOTIFY_PASSWORD` | mot de passe SMTP |
| `MW_NOTIFY_FROM` | expéditeur (par défaut : `MW_NOTIFY_USER`) |
| `MW_NOTIFY_TO` | destinataire des rapports |

Aucun dépôt client ne contient de mot de passe email.

## Versions

Les sites pointent sur un tag, jamais sur `main`. Les scripts sont récupérés
au **même tag** que le workflow appelé : une version est donc cohérente de
bout en bout.

| Situation | Action | Effet |
|---|---|---|
| Correction sans changement de comportement | déplacer le tag | tous les sites au déploiement suivant |
| Changement de comportement | publier `v3` | aucun, jusqu'à migration site par site |

## Hébergeurs

| Hébergeur | Protocole | Port | Chemin type |
|---|---|---|---|
| Infomaniak | `sftp` | 22 | `sites/domaine.ch/` |
| OVH mutualisé | `ftps` | 21 | `www/` |
| o2switch | `sftp` | 22 | `public_html/` |
| Hostinger | `ftp` | 21 | `public_html/` |

Ne jamais laisser `SFTP_REMOTE_PATH` vide ou à `.` : le déploiement viserait
tout le compte FTP. Le moteur détecte ce cas et désactive la suppression, mais
mieux vaut ne pas s'y trouver.

## Tests

```bash
python3 tests/run_tests.py
```

114 scénarios exécutés contre les vrais scripts, sans mock.
