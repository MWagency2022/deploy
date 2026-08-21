# MW Agency — Workflow de déploiement central

Ce dépôt contient **un seul fichier utile** : le workflow qui met en ligne les
sites clients. Aucun site n'est hébergé ici, aucune valeur propre à un client
n'y figure.

## Pourquoi ce dépôt existe

Chaque site client appelle ce workflow au lieu d'en posséder sa propre copie.
Une correction faite ici profite à tous les clients à leur prochain
déploiement — au lieu d'être à recoller dépôt par dépôt.

## Ce que fait le workflow

1. Installe les dépendances et lance le build
2. **Vérifie qu'un vrai fichier HTML a été produit** — sinon il s'arrête, pour
   ne jamais écraser un site en production par un dossier d'assets inutilisable
3. Sauvegarde la version en ligne dans un dossier daté, hors du dossier public
4. Envoie le nouveau site en miroir et supprime les fichiers obsolètes
5. Fait tourner les sauvegardes : la plus ancienne est gardée indéfiniment,
   plus les dix plus récentes

Les étapes de sauvegarde ne sont **jamais bloquantes** : un incident de
sauvegarde n'empêche pas un site de se mettre à jour.

## Brancher un site client

Dans le dépôt du client, créer `.github/workflows/deploy.yml` :

```yaml
name: Deploiement

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploiement:
    uses: MWagency2022/deploy/.github/workflows/static-deploy.yml@v1
    secrets: inherit
```

Puis créer les cinq secrets dans ce même dépôt — le script
`nouveau-client.sh` le fait en une commande.

## Secrets attendus

| Secret | Obligatoire | Exemple |
|---|---|---|
| `SFTP_HOST` | oui | `4805tb.ftp.infomaniak.com` |
| `SFTP_USERNAME` | oui | `4805tb_mwadmin` |
| `SFTP_PASSWORD` | oui | — |
| `SFTP_PORT` | non | `22` (défaut selon le protocole) |
| `SFTP_REMOTE_PATH` | oui | `sites/domaineduclient.ch/` |

Le chemin distant doit rester **relatif au compte FTP**. Un chemin absolu
casserait la réutilisabilité et fuiterait l'identifiant du compte.

## Réglages facultatifs

À ne toucher que si le client sort du cas standard :

| Réglage | Défaut | Quand le changer |
|---|---|---|
| `protocol` | `sftp` | Hébergeur en `ftps` ou `ftp` simple |
| `build_dir` | `dist/client` | Autre framework produisant `dist` ou `build` |
| `build_command` | `npm run build` | Commande de build non standard |
| `index_file` | `index.html` | Page d'entrée portant un autre nom |
| `node_version` | `20` | Projet exigeant une autre version |
| `backup` | `true` | Désactiver la sauvegarde sur un site jetable |
| `backup_keep` | `10` | Conserver plus ou moins d'historique |

## Versions

Les sites clients pointent sur un tag, jamais sur `main`.

```
git tag -a v1 -m "Version 1" && git push origin v1
```

Pour publier une correction sans casser la production :

```
git tag -f v1 && git push -f origin v1     # correctif compatible
git tag -a v2 && git push origin v2        # changement de comportement
```

Un changement qui modifie le comportement attendu doit sortir en `v2`, et les
clients y sont basculés un par un après vérification.

## Hébergeurs vérifiés

| Hébergeur | Protocole | Port | Chemin type |
|---|---|---|---|
| Infomaniak | `sftp` | 22 | `sites/domaine.ch/` |
| OVH mutualisé | `ftps` | 21 | `www/` |
| o2switch | `sftp` | 22 | `public_html/` |
| Hostinger | `ftp` | 21 | `public_html/` |

Compléter ce tableau à chaque nouvel hébergeur rencontré : c'est la mémoire
de l'agence.
