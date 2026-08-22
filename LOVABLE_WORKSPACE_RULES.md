# Règles d'espace de travail Lovable — MW Agency

Texte à coller **une seule fois** dans les règles / knowledge de l'espace de
travail Lovable (Settings → Knowledge).

Les règles ne s'appliquent qu'aux projets contenant `mw-config.json` **et**
`publier.txt`. Les autres projets de l'espace ne sont pas affectés.

---

## Texte à copier

```text
CONVENTION DE DÉPLOIEMENT MW AGENCY

Ces règles ne s'appliquent QUE si le projet contient à la fois un fichier
mw-config.json et un fichier publier.txt à sa racine. Si l'un des deux est
absent, ignore entièrement cette section.

mw-config.json est la source de vérité du déploiement. Il ressemble à ceci :

{
  "domain": "https://client.ch",
  "language": "fr",
  "status": "chantier",
  "localBusiness": true,
  "backup_path": "",
  "pages": ["/", "/services/", "/realisations/", "/contact/"]
}

RÈGLE 1 — « Passe le site en livré » / « Le client a validé »
Modifie uniquement mw-config.json : "status": "livre".
Ne publie pas. Ne touche à aucun autre fichier.
Réponds en confirmant que le site ne se mettra plus à jour tout seul et
qu'il faudra demander explicitement la publication.

RÈGLE 2 — « Repasse le site en chantier »
Modifie uniquement mw-config.json : "status": "chantier".
Ne publie pas.

RÈGLE 3 — « Publie le site » / « Mets le site en ligne »
Remplace le contenu de publier.txt par une demande horodatée, par exemple :

Demande de publication
Date : 2026-08-21 14:30 UTC
Identifiant : pub-20260821-1430

La valeur doit changer à chaque demande, sinon aucun commit n'est produit et
rien ne part. Ne modifie aucun autre fichier lors d'une demande de publication.

RÈGLE 4 — « Le domaine final est https://client.ch »
Mets à jour "domain" dans mw-config.json, puis corrige dans le projet les
métadonnées SEO qui doivent utiliser ce domaine : link canonical, og:url, et
toute URL absolue de métadonnée pointant encore vers un domaine de maquette,
une adresse lovable.app ou localhost.
Ne modifie pas les contenus éditoriaux au passage.

RÈGLE 5 — Liste des pages publiques (à maintenir SANS qu'on te le demande)
Le tableau "pages" de mw-config.json recense les URLs publiques du site.
Tu le mets à jour DE TOI-MÊME, dans le même changement, chaque fois que :
  - tu crées une page publique      -> ajoute son URL
  - tu supprimes une page publique  -> retire son URL
  - tu renommes une route           -> remplace l'ancienne URL par la nouvelle
N'attends jamais qu'on te le demande : c'est une conséquence automatique de la
modification, au même titre que la mise à jour d'un menu de navigation.

Format : URLs relatives, commençant et finissant par une barre oblique.
L'accueil s'écrit "/". Exemple : ["/", "/services/", "/contact/"].

N'y inscris PAS : la page 404, les pages de remerciement après formulaire, les
pages en noindex, ni aucune page technique. Uniquement les pages publiques
destinées à être indexées.

Le moteur de déploiement refuse la publication d'un site livré si une page
listée ici n'est pas réellement produite en HTML pré-rendu. Cette liste est
donc ce qui permet de détecter un prérendu partiel.

RÈGLE 6 — Exigences SEO permanentes
Chaque page publique indexable doit porter :
  - un attribut lang correspondant à "language" de mw-config.json
  - un title unique
  - une meta description de 50 à 160 caractères
  - un link rel="canonical" absolu vers sa propre URL sur le domaine configuré
  - og:title, og:description, og:image
  - un h1 unique
  - du contenu réellement présent dans le HTML rendu côté serveur
Si "localBusiness" vaut true, la page d'accueil doit porter un JSON-LD
d'entreprise (LocalBusiness, Organization ou sous-type adapté). Les autres
pages n'en ont pas besoin.
Le contenu du site doit être rendu au prérendu, pas uniquement après
hydratation JavaScript : une page dont le HTML initial est vide est refusée
par le moteur de déploiement. Le moteur ne corrige jamais cela lui-même — il
détecte, bloque et explique. C'est à toi de faire en sorte que chaque page
publique sorte du build avec son contenu déjà présent dans le HTML.

RÈGLE 7 — Ne jamais inventer
N'invente jamais une adresse, un numéro de téléphone, des horaires, un avis,
un témoignage, une certification, un prix, un nombre de clients ou des années
d'expérience — ni dans le contenu, ni dans les données structurées. Si une
information manque, demande-la.

RÈGLE 8 — Champs que tu ne touches jamais
Le champ "backup_path" de mw-config.json concerne l'hébergement, pas le site.
Ne le modifie jamais, même si on te demande de "nettoyer" ou "compléter" la
configuration. Il est renseigné par l'agence au branchement du site.

RÈGLE 9 — Secrets
Ne demande jamais, n'écris jamais et n'affiche jamais d'identifiants FTP,
SFTP, SMTP ou de mots de passe. Ils vivent uniquement dans les secrets GitHub
et ne concernent pas le projet Lovable.
```

---

## Ce que ça change concrètement

| Ce que tu dis dans Lovable | Ce que Lovable fait | Effet |
|---|---|---|
| « Le client a validé. Passe-le en livré. » | `"status": "livre"` | Les commits ne modifient plus la production |
| « Publie le site. » | Met à jour `publier.txt` | Déclenche la mise en ligne |
| « Le domaine final est … » | Met à jour `domain` + corrige les canonical | Le moteur valide les URLs |
| « Repasse en chantier. » | `"status": "chantier"` | Retour au déploiement continu |
| *(tu ajoutes ou supprimes une page)* | Met à jour `pages` tout seul | Le moteur vérifie que la page sort vraiment |

## Vérifier que la règle est prise en compte

Sur un projet branché, demander : *« Quel est le statut du site ? »*
Lovable doit répondre en lisant `mw-config.json`, pas en devinant.
