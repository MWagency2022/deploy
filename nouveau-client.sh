#!/usr/bin/env bash
#
#  MW Agency — Branchement d'un nouveau site
#
#  Procédure guidée. Après ce script, tout se passe dans Lovable.
#
#  Prérequis : GitHub CLI installé et connecté
#      brew install gh          (macOS)
#      winget install GitHub.cli (Windows)
#      gh auth login
#
set -euo pipefail

MOTEUR_DEPOT="MWagency2022/deploy"
MOTEUR_VERSION="v2"        # version stable par defaut

# --version permet de brancher un site sur une version de test du moteur.
while [ $# -gt 0 ]; do
  case "$1" in
    --version)
      [ -n "${2:-}" ] || { echo "Usage : $0 --version <tag>"; exit 1; }
      MOTEUR_VERSION="$2"; shift 2 ;;
    --version=*)
      MOTEUR_VERSION="${1#*=}"; shift ;;
    -h|--help)
      echo "Usage : $0 [--version <tag du moteur>]"
      echo "  Defaut : $MOTEUR_VERSION"
      exit 0 ;;
    *)
      echo "Option inconnue : $1"; echo "Usage : $0 [--version <tag>]"; exit 1 ;;
  esac
done

echo "=================================================="
echo " MW Agency — branchement d'un nouveau site"
echo " Moteur : $MOTEUR_DEPOT@$MOTEUR_VERSION"
echo "=================================================="
echo
if [ "$MOTEUR_VERSION" != "v2" ]; then
  echo " ATTENTION : version de moteur non stable ($MOTEUR_VERSION)."
  echo " A n'utiliser que pour un site de test."
  echo
fi

command -v gh >/dev/null 2>&1 || {
  echo "GitHub CLI (gh) n'est pas installé."
  echo "  macOS   : brew install gh"
  echo "  Windows : winget install GitHub.cli"
  exit 1
}
gh auth status >/dev/null 2>&1 || { echo "Lance d'abord : gh auth login"; exit 1; }

demander() {           # demander VARIABLE "question" "valeur par défaut"
  local var=$1 question=$2 defaut=${3:-} reponse
  if [ -n "$defaut" ]; then
    read -r -p "$question [$defaut] : " reponse
    reponse=${reponse:-$defaut}
  else
    read -r -p "$question : " reponse
  fi
  while [ -z "$reponse" ]; do
    read -r -p "  (obligatoire) $question : " reponse
  done
  printf -v "$var" '%s' "$reponse"
}

demander DEPOT   "Dépôt GitHub (ex. MWagency2022/konstructa)"
demander DOMAINE "Domaine final (ex. https://konstructa.ch)"
demander LANGUE  "Langue principale" "fr"
demander LOCAL   "Entreprise locale (oui/non)" "oui"
demander HEBERGEUR "Hébergeur (Infomaniak, OVH, o2switch...)" "Infomaniak"
demander PROTO   "Protocole (sftp/ftps/ftp)" "sftp"
demander HOTE    "Hôte FTP (ex. 4805tb.ftp.infomaniak.com)"
demander UTIL    "Utilisateur FTP"
read -r -s -p "Mot de passe FTP (saisie masquée) : " MOTDEPASSE; echo
demander CHEMIN  "Dossier distant (ex. sites/konstructa.ch/)"

case "$PROTO" in sftp) PORT_DEFAUT=22 ;; *) PORT_DEFAUT=21 ;; esac
demander PORT "Port" "$PORT_DEFAUT"

[ -n "$MOTDEPASSE" ] || { echo "Mot de passe obligatoire."; exit 1; }
[[ "$DOMAINE" =~ ^https?://[^/]+$ ]] || { echo "Domaine invalide : attendu https://exemple.ch"; exit 1; }
case "$CHEMIN" in
  ""|"."|"/") echo "Le dossier distant ne peut pas être la racine du compte FTP."; exit 1 ;;
  /*) echo "Attention : chemin absolu. Il doit être relatif au compte FTP."
      read -r -p "Continuer ? (o/N) " c; [ "$c" = "o" ] || exit 1 ;;
esac
[ "$LOCAL" = "oui" ] && LOCAL_JSON=true || LOCAL_JSON=false

echo
echo "--------------------------------------------------"
echo " Dépôt      : $DEPOT"
echo " Domaine    : $DOMAINE"
echo " Hébergeur  : $HEBERGEUR ($PROTO, port $PORT)"
echo " Dossier    : $CHEMIN"
echo " Mot de passe : ******** (non affiché)"
echo "--------------------------------------------------"
read -r -p "Confirmer ? (o/N) " c; [ "$c" = "o" ] || { echo "Annulé."; exit 1; }

echo
echo "1/4  Secrets GitHub"
printf '%s' "$HOTE"        | gh secret set SFTP_HOST        --repo "$DEPOT"
printf '%s' "$UTIL"        | gh secret set SFTP_USERNAME    --repo "$DEPOT"
printf '%s' "$MOTDEPASSE"  | gh secret set SFTP_PASSWORD    --repo "$DEPOT"
printf '%s' "$PORT"        | gh secret set SFTP_PORT        --repo "$DEPOT"
printf '%s' "$CHEMIN"      | gh secret set SFTP_REMOTE_PATH --repo "$DEPOT"
unset MOTDEPASSE
echo "     5 secrets créés (le mot de passe n'a été ni affiché ni écrit sur disque)."

echo
echo "2/4  Fichiers du site"
TRAVAIL=$(mktemp -d)
trap 'rm -rf "$TRAVAIL"' EXIT
gh repo clone "$DEPOT" "$TRAVAIL/site" -- --depth 1 >/dev/null 2>&1
cd "$TRAVAIL/site"
mkdir -p .github/workflows

cat > mw-config.json <<JSON
{
  "domain": "$DOMAINE",
  "language": "$LANGUE",
  "status": "chantier",
  "localBusiness": $LOCAL_JSON,
  "backup_path": "",
  "pages": [
    "/"
  ]
}
JSON

cat > publier.txt <<TXT
Ce fichier declenche la mise en ligne du site.

Quand le site est en statut "livre", une modification de ce fichier
vaut ordre de publication. Dire dans Lovable : "publie le site".

Derniere demande de publication :
(aucune)
TXT

AVEC_PROTO=""
[ "$PROTO" != "sftp" ] && AVEC_PROTO="      protocol: $PROTO"

cat > .github/workflows/deploy.yml <<YAML
# Deploiement - MW Agency
# Ce fichier n'a pas a etre modifie : tous les reglages du site
# vivent dans mw-config.json.

name: Deploiement

on:
  push:
    branches:
      - main
  workflow_dispatch:
    inputs:
      adopter_dossier_distant:
        description: "Adopter un dossier distant non vide sans marqueur MW Agency"
        type: boolean
        default: false

jobs:
  deploiement:
    uses: $MOTEUR_DEPOT/.github/workflows/static-deploy.yml@$MOTEUR_VERSION
    secrets: inherit
    with:
      adopter_dossier_distant: \${{ inputs.adopter_dossier_distant == true }}
$AVEC_PROTO
YAML

cat > .github/workflows/restore.yml <<YAML
# Restauration - MW Agency
# Actions > Restauration > Run workflow, sans rien remplir pour voir la liste.

name: Restauration

on:
  workflow_dispatch:
    inputs:
      sauvegarde:
        description: "Nom de la sauvegarde (vide = afficher la liste)"
        type: string
        required: false
        default: ""
      confirmer:
        description: "Je confirme l ecrasement du site en ligne"
        type: boolean
        required: false
        default: false

jobs:
  restauration:
    uses: $MOTEUR_DEPOT/.github/workflows/static-restore.yml@$MOTEUR_VERSION
    secrets: inherit
    with:
      backup: \${{ inputs.sauvegarde }}
      confirm: \${{ inputs.confirmer }}
YAML

git add mw-config.json publier.txt .github/workflows/deploy.yml .github/workflows/restore.yml
if git diff --cached --quiet; then
  echo "     Rien à ajouter : les fichiers étaient déjà à jour."
else
  git -c user.name="MW Agency" -c user.email="info@mwagency.ch" \
      commit -q -m "Branchement au moteur de deploiement MW Agency"
  git push -q
  echo "     mw-config.json, publier.txt et les deux workflows sont en place."
fi
cd - >/dev/null

echo
echo "3/4  Inventaire"
echo "     Ajouter cette ligne dans clients.md du dépôt $MOTEUR_DEPOT :"
echo
echo "| ${DOMAINE#https://} | ${DEPOT##*/} | $HEBERGEUR | $PROTO | \`$CHEMIN\` | chantier | $MOTEUR_VERSION | — |"

echo
echo "4/4  Premier déploiement"
echo "     Le site est en statut chantier : chaque modification part en ligne."
echo "     Lance un premier déploiement pour valider le branchement :"
echo
echo "       gh workflow run Deploiement --repo $DEPOT"
echo

echo "=================================================="
echo " SITE BRANCHÉ AU SYSTÈME MW AGENCY"
echo "=================================================="
echo
echo " Il ne reste plus qu'à travailler dans Lovable."
echo
echo " Quand le client valide :  « Le client a validé le site. Passe-le en livré. »"
echo " Pour mettre en ligne   :  « Publie le site. »"
