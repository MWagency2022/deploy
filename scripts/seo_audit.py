"""Audit SEO du HTML reellement servi aux moteurs.

N'interrompt jamais le processus lui-meme : il enregistre ses conclusions dans
mw-report.json et laisse le workflow decider. C'est ce qui garantit que le
rapport et l'email partent meme en cas de blocage.
"""
import json, os, re, sys, glob
import mw_common as mw

dossier = sys.argv[1]
domaine = (sys.argv[2] or '').rstrip('/')
langue  = sys.argv[3] if len(sys.argv) > 3 else 'fr'
mode    = sys.argv[4] if len(sys.argv) > 4 else 'rapport'   # non | rapport | strict
local   = (sys.argv[5] if len(sys.argv) > 5 else 'true') == 'true'

# Un seuil unique pour tout le site n'a pas de sens : une page contact courte
# est legitime, une page d'accueil vide ne l'est pas.
SEUIL_ERREUR_PRINCIPALE = 250
SEUIL_ALERTE_PRINCIPALE = 600
SEUIL_ALERTE_SECONDAIRE = 150

TYPES_ENTREPRISE = {
    'LocalBusiness', 'Organization', 'ProfessionalService', 'Store',
    'Restaurant', 'HomeAndConstructionBusiness', 'GeneralContractor',
    'HomeGoodsStore', 'FurnitureStore', 'Corporation', 'LegalService',
    'MedicalBusiness', 'HealthAndBeautyBusiness', 'FoodEstablishment',
}

r = mw.charger()
pages = sorted(glob.glob(os.path.join(dossier, '**', '*.html'), recursive=True))

if not pages:
    mw.probleme(r, 'build', 'html', "Aucune page HTML dans le build.",
                "Verifier la commande de build et le prerendu.")
    r['seo'] = 'failed'; r['status_global'] = 'blocked'
    mw.sauver(r); print("Aucune page HTML."); sys.exit(0)

print("=" * 68)
print(f" AUDIT SEO - {len(pages)} page(s) - mode {mode}")
print(f" Domaine de reference : {domaine or '(non configure)'}")
print("=" * 68)

accueil_a_schema = False
schema_present_ailleurs = []
titres_vus = {}          # titre -> [pages]
descriptions_vues = {}   # description -> [pages]

for chemin in pages:
    rel = os.path.relpath(chemin, dossier).replace(os.sep, '/')
    s = open(chemin, encoding='utf-8', errors='replace').read()
    nom = mw.slug(rel).upper()
    classe = mw.classe_page(rel)
    noindex = mw.est_noindex(s)
    indexable = not noindex and classe != 'technique'

    print(f"\n--- {rel}  [{classe}{' / noindex' if noindex else ''}] ---")

    # ---------------------------------------------------------- langue
    mh = re.search(r'<html[^>]*>', s, re.I)
    lg = mw.attribut(mh.group(0), 'lang') if mh else None
    if not lg:
        mw.probleme(r, nom, 'lang', "Attribut lang absent sur <html>.",
                    f"Definir lang=\"{langue}\" sur la balise <html>.",
                    None, langue)
    elif not lg.lower().startswith(langue.lower()):
        mw.probleme(r, nom, 'lang',
                    f"La page est declaree en \"{lg}\" alors que le site est en \"{langue}\".",
                    f"Remplacer lang=\"{lg}\" par lang=\"{langue}\".", lg, langue)
    else:
        print(f"  lang            OK   {lg}")

    # ---------------------------------------------------------- titre
    mt = re.search(r'<title[^>]*>(.*?)</title>', s, re.I | re.S)
    titre = mw.texte_de(mt.group(1)) if mt else ''
    if not titre:
        mw.probleme(r, nom, 'title', "Balise <title> absente ou vide.",
                    "Definir un titre unique et descriptif pour cette page.")
    else:
        print(f"  title           OK   ({len(titre)}) {titre[:52]}")
        if indexable:
            titres_vus.setdefault(titre.strip().lower(), []).append(nom)
        if indexable and not (10 <= len(titre) <= 65):
            mw.avertir(r, nom, 'title',
                       f"Titre de {len(titre)} caracteres (viser 10 a 65).",
                       "Ajuster la longueur du titre.", titre, "10 a 65 caracteres")

    # ---------------------------------------------------------- description
    desc = mw.meta(s, nom='description')
    if not desc:
        if indexable:
            mw.probleme(r, nom, 'description', "Meta description absente.",
                        "Ajouter une meta description de 50 a 160 caracteres.")
    else:
        print(f"  description     OK   ({len(desc)})")
        if indexable:
            descriptions_vues.setdefault(desc.strip().lower(), []).append(nom)
        if indexable and not (50 <= len(desc) <= 160):
            mw.avertir(r, nom, 'description',
                       f"Description de {len(desc)} caracteres (viser 50 a 160).",
                       "Ajuster la longueur de la meta description.",
                       f"{len(desc)} caracteres", "50 a 160 caracteres")

    # ---------------------------------------------------------- canonique
    canon = mw.canonique(s)
    attendue = mw.url_attendue(rel, domaine) if domaine else None

    if indexable:
        if not canon:
            mw.probleme(r, nom, 'canonical', "Balise canonical absente.",
                        f"Ajouter <link rel=\"canonical\" href=\"{attendue or 'URL absolue de la page'}\">",
                        None, attendue)
        else:
            mauvais = mw.hote_interdit(canon)
            if mauvais:
                mw.probleme(r, nom, 'canonical',
                            f"La canonical pointe vers un domaine de developpement ({mauvais}).",
                            f"Remplacer la canonical par {attendue or 'le domaine final'}.",
                            canon, attendue)
            elif not re.match(r'(?i)^https?://', canon):
                mw.probleme(r, nom, 'canonical',
                            "La canonical est relative alors qu'elle doit etre absolue.",
                            f"Utiliser l'URL absolue {attendue or 'du domaine final'}.",
                            canon, attendue)
            elif attendue and mw.normaliser(canon) != mw.normaliser(attendue):
                mw.probleme(r, nom, 'canonical',
                            "La canonical ne correspond pas a l'URL de la page.",
                            f"Faire pointer la canonical de cette page vers {attendue}.",
                            canon, attendue)
            else:
                print(f"  canonical       OK   {canon}")

    if noindex:
        print("  robots          noindex - page exclue de l'indexation")

    # ---------------------------------------------------------- partage social
    for prop in ('og:title', 'og:description', 'og:image'):
        v = mw.meta(s, prop=prop)
        if v:
            print(f"  {prop:15s} OK")
        elif indexable:
            mw.probleme(r, nom, prop, f"{prop} absent.",
                        f"Ajouter la balise {prop} pour l'aperçu au partage.")

    ogurl = mw.meta(s, prop='og:url')
    if ogurl and indexable:
        mauvais = mw.hote_interdit(ogurl)
        if mauvais:
            mw.probleme(r, nom, 'og:url',
                        f"og:url pointe vers un domaine de developpement ({mauvais}).",
                        f"Remplacer og:url par {attendue or 'le domaine final'}.",
                        ogurl, attendue)
        elif canon and mw.normaliser(ogurl) != mw.normaliser(canon):
            mw.probleme(r, nom, 'og:url',
                        "og:url ne correspond pas a la canonical.",
                        "Aligner og:url sur la canonical de la page.", ogurl, canon)
        else:
            print("  og:url          OK")
    elif indexable:
        mw.avertir(r, nom, 'og:url', "og:url absent.",
                   f"Ajouter og:url avec {attendue or 'l URL absolue de la page'}.")

    # ------------------------------------------- autres URLs SEO douteuses
    for prop in ('og:image', 'twitter:image'):
        v = mw.meta(s, prop=prop)
        mauvais = mw.hote_interdit(v) if v else None
        if mauvais:
            mw.probleme(r, nom, prop,
                        f"{prop} pointe vers un domaine de developpement ({mauvais}).",
                        f"Heberger l'image sur {domaine or 'le domaine final'}.", v, None)

    # ---------------------------------------------------------- titre h1
    h1 = re.findall(r'(?is)<h1[^>]*>(.*?)</h1>', s)
    if not h1:
        if classe == 'principale' and indexable:
            mw.probleme(r, nom, 'h1', "Aucun <h1> dans le HTML servi.",
                        "Ajouter un titre principal <h1> a cette page.")
        elif indexable:
            mw.avertir(r, nom, 'h1', "Aucun <h1> dans le HTML servi.",
                       "Ajouter un titre principal <h1>.")
    else:
        if len(h1) > 1 and indexable:
            mw.avertir(r, nom, 'h1', f"{len(h1)} balises <h1> (une seule recommandee).",
                       "Ne conserver qu'un seul <h1> par page.")
        print(f"  h1              OK   {mw.texte_de(h1[0])[:52]}")

    # ------------------------------------------- contenu lisible sans JS
    principal = mw.contenu_principal(s)
    n = len(principal)
    if classe == 'technique':
        print(f"  contenu         {n} car. (page technique, pas de seuil)")
    elif classe == 'secondaire':
        print(f"  contenu         {n} car.")
        if n < SEUIL_ALERTE_SECONDAIRE:
            mw.avertir(r, nom, 'contenu',
                       f"Contenu principal court ({n} caracteres).",
                       "Verifier que la page rend bien son contenu sans JavaScript.",
                       f"{n} caracteres", f"{SEUIL_ALERTE_SECONDAIRE}+ caracteres")
    else:
        if n < SEUIL_ERREUR_PRINCIPALE:
            mw.probleme(r, nom, 'html-vide',
                        f"Le HTML initial de cette page est presque vide. "
                        f"{n} caracteres de contenu principal detectes. "
                        f"Le contenu semble dependre entierement de JavaScript.",
                        "Activer le prerendu du projet (prerender dans vite.config) "
                        "et verifier qu'aucun composant ne rend du vide cote serveur.",
                        f"{n} caracteres", f"{SEUIL_ERREUR_PRINCIPALE}+ caracteres")
        else:
            print(f"  contenu         OK   {n} caracteres")
            if n < SEUIL_ALERTE_PRINCIPALE:
                mw.avertir(r, nom, 'contenu',
                           f"Contenu principal un peu court ({n} caracteres).",
                           "Etoffer le contenu editorial de cette page.")

    # ------------------------------------------- images sans alternative
    images = re.findall(r'(?i)<img[^>]*>', s)
    sans_alt = [i for i in images if mw.attribut(i, 'alt') is None]
    if sans_alt:
        mw.avertir(r, nom, 'alt',
                   f"{len(sans_alt)} image(s) sur {len(images)} sans attribut alt.",
                   "Ajouter une alternative textuelle decrivant chaque image.",
                   f"{len(sans_alt)} sans alt", "toutes avec alt")

    # ---------------------------------------------------------- JSON-LD
    types = []
    for bloc in mw.blocs_jsonld(s):
        try:
            data = json.loads(bloc.strip())
        except Exception as e:
            mw.probleme(r, nom, 'jsonld',
                        f"Un bloc de donnees structurees est syntaxiquement invalide ({e}).",
                        "Corriger le JSON-LD de cette page.")
            continue
        for item in (data if isinstance(data, list) else [data]):
            if isinstance(item, dict):
                g = item.get('@graph')
                cibles = g if isinstance(g, list) else [item]
                for c in cibles:
                    if isinstance(c, dict):
                        t = c.get('@type')
                        types += t if isinstance(t, list) else ([t] if t else [])
    if types:
        print(f"  donnees struct. OK   {', '.join(types)}")
    if set(types) & TYPES_ENTREPRISE:
        if mw.slug(rel) == 'accueil':
            accueil_a_schema = True
        else:
            schema_present_ailleurs.append(nom)

# ------------------------------------------------- doublons de metadonnees
for valeur, pages_concernees in titres_vus.items():
    if len(pages_concernees) > 1:
        mw.avertir(r, ' / '.join(pages_concernees), 'title-double',
                   f"Titre identique sur {len(pages_concernees)} pages.",
                   "Donner un titre distinct a chaque page.",
                   valeur[:80], "un titre unique par page")

for valeur, pages_concernees in descriptions_vues.items():
    if len(pages_concernees) > 1:
        mw.avertir(r, ' / '.join(pages_concernees), 'description-double',
                   f"Meta description identique sur {len(pages_concernees)} pages.",
                   "Donner une description distincte a chaque page.",
                   valeur[:80], "une description unique par page")

# ------------------------------------------------- schema entreprise global
if local and domaine is not None:
    if accueil_a_schema:
        print("\n  Balisage entreprise present sur l'accueil.")
    else:
        mw.probleme(r, 'ACCUEIL', 'schema',
                    "Aucun balisage entreprise (LocalBusiness, Organization ou "
                    "sous-type equivalent) sur la page d'accueil.",
                    "Ajouter un bloc JSON-LD entreprise sur l'accueil, avec les "
                    "informations reelles du client uniquement.")

# ---------------------------------------------------------------- robots.txt
print("\n--- robots.txt ---")
chemin_robots = os.path.join(dossier, 'robots.txt')
if os.path.isfile(chemin_robots):
    contenu = open(chemin_robots, encoding='utf-8', errors='replace').read()
    blocs = re.split(r'(?im)^\s*user-agent\s*:', contenu)
    for b in blocs[1:]:
        agent = b.splitlines()[0].strip().lower()
        regles = [l.strip() for l in b.splitlines()[1:]]
        bloque_tout = any(re.match(r'(?i)^disallow\s*:\s*/\s*$', l) for l in regles)
        if bloque_tout:
            if agent == '*':
                mw.probleme(r, 'ROBOTS', 'robots',
                            "robots.txt interdit l'indexation de tout le site "
                            "(User-agent: * / Disallow: /).",
                            "Retirer cette regle avant la mise en ligne.",
                            "Disallow: /", "Allow: /")
            else:
                mw.avertir(r, 'ROBOTS', 'robots',
                           f"robots.txt bloque entierement \"{agent}\".",
                           "Verifier que ce blocage est voulu.")
    if not re.search(r'(?im)^\s*sitemap\s*:', contenu):
        mw.avertir(r, 'ROBOTS', 'robots', "robots.txt ne reference pas le sitemap.",
                   "La reference est ajoutee automatiquement si le domaine est configure.")
    else:
        print("  robots.txt      OK")
else:
    mw.avertir(r, 'ROBOTS', 'robots', "robots.txt absent.",
               "Il est cree automatiquement si le domaine est configure.")

# ---------------------------------------------------------------- verdict
r['seo'] = 'failed' if r['errors'] else 'ok'
if r['errors'] and mode == 'strict':
    r['status_global'] = 'blocked'

print("\n" + "=" * 68)
print(f" {len(r['errors'])} probleme(s) bloquant(s), {len(r['warnings'])} avertissement(s)")
if mode == 'rapport' and r['errors']:
    print(" Mode rapport : la mise en ligne continue malgre les problemes.")
if mode == 'strict' and r['errors']:
    print(" Mode strict : la mise en ligne sera interrompue.")
print("=" * 68)

mw.sauver(r)
sys.exit(0)
