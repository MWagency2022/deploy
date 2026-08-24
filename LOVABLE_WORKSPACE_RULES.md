# Règles d'espace de travail Lovable — MW Agency

Texte à coller **une seule fois** dans les règles / knowledge de l'espace de
travail Lovable (Settings → Knowledge). C'est un réglage de l'espace : il vaut
pour tous les projets, présents et futurs. Ne le recolle jamais dans un projet.

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
Réponds en confirmant que le site ne se mettra plus à jour tout seul et qu'il
faudra demander explicitement la publication.

RÈGLE 2 — « Repasse le site en chantier »
Modifie uniquement mw-config.json : "status": "chantier". Ne publie pas.

RÈGLE 3 — « Publie le site » / « Mets le site en ligne »
Remplace le contenu de publier.txt par une demande horodatée, par exemple :

Demande de publication
Date : 2026-08-21 14:30 UTC
Identifiant : pub-20260821-1430

La valeur doit changer à chaque demande, sinon aucun commit n'est produit et rien
ne part. Ne modifie aucun autre fichier lors d'une demande de publication.

RÈGLE 4 — « Le domaine final est https://client.ch »
Mets à jour "domain" dans mw-config.json, puis corrige dans le projet les
métadonnées SEO qui doivent utiliser ce domaine : link canonical, og:url, et toute
URL absolue de métadonnée pointant encore vers un domaine de maquette, une adresse
lovable.app ou localhost. Ne modifie pas les contenus éditoriaux au passage.

RÈGLE 5 — Liste des pages publiques, à maintenir SANS qu'on te le demande
Le tableau "pages" de mw-config.json recense les URLs publiques du site.
Tu le mets à jour DE TOI-MÊME, dans le même changement, chaque fois que :
  - tu crées une page publique      -> ajoute son URL
  - tu supprimes une page publique  -> retire son URL
  - tu renommes une route           -> remplace l'ancienne URL par la nouvelle
N'attends jamais qu'on te le demande : c'est une conséquence automatique de la
modification, au même titre que la mise à jour d'un menu de navigation.
Format : URLs relatives, commençant et finissant par une barre oblique.
L'accueil s'écrit "/". Exemple : ["/", "/services/", "/contact/"].
N'y inscris PAS : la page 404, les pages de remerciement, les pages en noindex, ni
aucune page technique. Uniquement les pages publiques destinées à être indexées.

RÈGLE 6 — Exigences SEO permanentes
Chaque page publique indexable doit porter :
  - un attribut lang correspondant à "language" de mw-config.json
  - un title unique
  - une meta description de 50 à 160 caractères
  - un link rel="canonical" absolu vers sa propre URL sur le domaine configuré,
    AVEC une barre oblique finale
  - og:title, og:description, og:image en URL absolue, og:url identique à la
    canonical
  - un h1 unique
  - au moins 250 caractères de contenu réel dans le HTML servi, mesurés dans
    <main> s'il existe, sinon dans <body> privé de header, nav, footer et aside
Si "localBusiness" vaut true, la page d'accueil doit porter un JSON-LD
d'entreprise. Les autres pages n'en ont pas besoin.

RÈGLE 7 — Le contenu doit exister dans le HTML, pas seulement après JavaScript
Le site est prérendu statiquement au build : chaque page publique produit un
fichier HTML contenant son contenu réel. Une page dont le HTML initial est vide
est refusée par le moteur de déploiement.
Aucun composant ne doit renvoyer null, un écran de substitution ou un rendu réduit
selon la largeur de la fenêtre, selon un état de chargement, ou selon une mesure
faite dans le navigateur. Le contenu réel doit exister dans le rendu initial, à
toute largeur, sans JavaScript exécuté.

RÈGLE 8 — Rien ne s'installe à la main
Le serveur est le miroir exact du dossier de build. Tout fichier déposé à la main
sur le serveur disparaît au déploiement suivant.
Ne propose donc jamais : une librairie à installer sur le serveur, un fichier à
déposer par FTP, un mot de passe à saisir après coup, un build local, un export
manuel, ou une correction à faire directement en production. Tout ce dont le site
a besoin doit vivre dans le projet.

RÈGLE 9 — Ce que le moteur produit, ne le fabrique pas
Le moteur de déploiement génère à chaque publication : le sitemap.xml (toujours
réécrit), le fichier .htaccess (sauf si le projet en fournit un dans public/), et
un marqueur d'identité du site. Il complète le robots.txt du projet avec la ligne
du sitemap.
Ne fabrique jamais de sitemap.xml. N'écris pas la ligne Sitemap dans robots.txt.
Ne prépare aucun export.

RÈGLE 10 — Formulaire de contact
Un seul mécanisme : public/api/contact.php, fichier autonome utilisant la fonction
PHP native mail(). Jamais PHPMailer, jamais Composer, jamais SMTP authentifié,
jamais Web3Forms, Formspree, Netlify Forms ou mailto. Le formulaire pointe vers
/api/contact.php et redirige vers /thank-you.html.

RÈGLE 11 — Design validé
Une fois la maquette validée par le client, le design est gelé. Ne redesign pas,
ne change ni les couleurs, ni la typographie, ni les textes commerciaux validés,
ni l'ordre des sections, ni le responsive déjà en place. Les étapes de production
ajoutent des fonctions, elles ne rejouent pas la direction artistique.

RÈGLE 12 — Ne jamais inventer
N'invente jamais une adresse, un numéro de téléphone, un numéro IDE, des horaires,
un avis, un témoignage, une certification, un prix, un nombre de clients, des
années d'expérience, un responsable légal ou un hébergeur — ni dans le contenu, ni
dans les données structurées, ni dans les pages légales. Si une information
manque : un champ [À COMPLÉTER] visible, jamais une valeur plausible.

RÈGLE 13 — Aucune trace de maquette en production
Ni localhost, ni *.lovable.app, ni *.vercel.app, ni *.netlify.app, ni example.com
dans les fichiers de production. Aucun titre générique visible : « New Project »,
« Website », « Landing Page », « Vite App », « React App », « Untitled ».
Le favicon n'est jamais le cœur ni le logo Lovable.
Le crédit « Powered by MW Agency » présent dans le footer est conservé, avec son
lien vers https://www.mwagency.ch.

RÈGLE 14 — Champs que tu ne touches jamais
Le champ "backup_path" de mw-config.json concerne l'hébergement, pas le site. Ne
le modifie jamais, même si on te demande de « nettoyer » ou « compléter » la
configuration. Il est renseigné par l'agence au branchement du site.

RÈGLE 15 — Secrets
Ne demande jamais, n'écris jamais et n'affiche jamais d'identifiants FTP, SFTP,
SMTP, de clé d'API ou de mot de passe. Ils vivent uniquement dans les secrets
GitHub et ne concernent pas le projet Lovable.

RÈGLE 16 — Pas de serveur à l'exécution
Le site doit rester 100 % statique une fois construit : aucun serveur Node à
l'exécution, aucun rendu serveur à la demande, aucune fonction serverless, aucune
base de données, aucun service externe pour le formulaire. Le prérendu est une
étape de build, pas une dépendance d'exécution. Le dossier de sortie est dist/.
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
