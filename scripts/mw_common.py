"""Fonctions partagees par les scripts du moteur MW Agency."""
import glob, json, os, re, sys, html as _html

RAPPORT = os.environ.get('MW_REPORT', 'mw-report.json')

MODELE = {
    "domain": "", "language": "fr", "status": "chantier",
    "localBusiness": True, "published": False, "status_global": "ok",
    "build": "not_started", "buildDir": "", "seo": "not_started",
    "identity": "not_started", "backup": "not_started",
    "deploy": "not_started", "productionCheck": "not_started",
    "rollback": "none", "errors": [], "warnings": [], "infos": [],
}


def charger():
    if os.path.isfile(RAPPORT):
        with open(RAPPORT, encoding='utf-8') as f:
            return json.load(f)
    return dict(MODELE, errors=[], warnings=[], infos=[])


def sauver(r):
    with open(RAPPORT, 'w', encoding='utf-8') as f:
        json.dump(r, f, ensure_ascii=False, indent=2)


# Un probleme releve soit du site (Lovable peut le corriger), soit de
# l'infrastructure (aucun prompt Lovable n'y changera quoi que ce soit).
TYPES_TECHNIQUES = {
    'identite', 'backup', 'ftp', 'production', 'notification', 'connexion',
}


def categorie_de(type_):
    return 'technique' if type_ in TYPES_TECHNIQUES else 'lovable'


def probleme(r, page, type_, message, action, trouve=None, attendu=None,
             categorie=None):
    r['errors'].append({
        "page": page, "type": type_, "found": trouve, "expected": attendu,
        "message": message, "action": action,
        "category": categorie or categorie_de(type_),
    })


def avertir(r, page, type_, message, action=None, trouve=None, attendu=None,
            categorie=None):
    r['warnings'].append({
        "page": page, "type": type_, "found": trouve, "expected": attendu,
        "message": message, "action": action,
        "category": categorie or categorie_de(type_),
    })


def info(r, texte):
    r['infos'].append(texte)


# ---------------------------------------------------------------- HTML

def sans_scripts(s):
    return re.sub(r'(?is)<(script|style|noscript|template)[^>]*>.*?</\1>', ' ', s)


def texte_de(s):
    t = _html.unescape(re.sub(r'<[^>]+>', ' ', sans_scripts(s)))
    return re.sub(r'\s+', ' ', t).strip()


def contenu_principal(s):
    """Texte du <main> si present, sinon <body> prive de header/nav/footer/aside."""
    m = re.search(r'(?is)<main[^>]*>(.*?)</main>', s)
    if m:
        return texte_de(m.group(1))
    b = re.search(r'(?is)<body[^>]*>(.*?)</body>', s)
    zone = b.group(1) if b else s
    for balise in ('header', 'nav', 'footer', 'aside'):
        zone = re.sub(rf'(?is)<{balise}[^>]*>.*?</{balise}>', ' ', zone)
    return texte_de(zone)


def attribut(balise, nom):
    """Lit un attribut en respectant le guillemet ouvrant (les apostrophes du
    texte francais ne doivent pas tronquer la valeur)."""
    m = re.search(rf'{nom}\s*=\s*(["\'])(.*?)\1', balise, re.I | re.S)
    return m.group(2) if m else None


def tete(s):
    i = s.lower().find('</head>')
    return s[:i] if i > 0 else s


def meta(s, nom=None, prop=None):
    zone = tete(s)
    if nom:
        m = re.search(rf'<meta[^>]*name\s*=\s*(["\']){re.escape(nom)}\1[^>]*>', zone, re.I)
    else:
        m = re.search(rf'<meta[^>]*property\s*=\s*(["\']){re.escape(prop)}\1[^>]*>', zone, re.I)
    return attribut(m.group(0), 'content') if m else None


def canonique(s):
    m = re.search(r'<link[^>]*rel\s*=\s*(["\'])canonical\1[^>]*>', tete(s), re.I)
    return attribut(m.group(0), 'href') if m else None


def blocs_jsonld(s):
    return re.findall(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        s, re.I | re.S)


def est_noindex(s):
    c = meta(s, nom='robots') or ''
    return 'noindex' in c.lower()


# ---------------------------------------------------------------- URLs

TECHNIQUES = ('404', 'thank-you', 'thankyou', 'merci', 'thanks', '500', 'offline')
SECONDAIRES = ('contact', 'mentions', 'mentions-legales', 'legal', 'privacy',
               'confidentialite', 'politique-de-confidentialite', 'cgv', 'cgu',
               'conditions', 'plan-du-site', 'sitemap')


# Fichiers de verification Google Search Console (googleXXXX.html a la racine).
# Ils sont deployes et servis tels quels, mais ce ne sont pas des pages du
# site : ni audit SEO, ni sitemap, ni classement editorial.
VERIFICATION = re.compile(r'(?i)^google[0-9a-f]{8,}\.html$')


def est_verification(rel):
    return bool(VERIFICATION.match(rel.replace(os.sep, '/')))


def fichiers_verification(dossier):
    return sorted(os.path.relpath(p, dossier).replace(os.sep, '/')
                  for p in glob.glob(os.path.join(dossier, '*.html'))
                  if est_verification(os.path.relpath(p, dossier)))


def pages_html(dossier):
    """Pages editoriales du build : tous les .html sauf les fichiers de verification."""
    tous = sorted(glob.glob(os.path.join(dossier, '**', '*.html'), recursive=True))
    return [p for p in tous if not est_verification(os.path.relpath(p, dossier))]


def url_attendue(rel, domaine):
    """URL canonique logique d'un fichier HTML du build."""
    rel = rel.replace(os.sep, '/')
    base = domaine.rstrip('/')
    if rel == 'index.html':
        return base + '/'
    if rel.endswith('/index.html'):
        return f"{base}/{rel[:-len('/index.html')]}/"
    return f"{base}/{rel[:-len('.html')]}/"


def slug(rel):
    rel = rel.replace(os.sep, '/')
    if rel == 'index.html':
        rel = ''                      # la racine du site, pas une page "index"
    elif rel.endswith('/index.html'):
        rel = rel[:-len('/index.html')]
    elif rel.endswith('.html'):
        rel = rel[:-len('.html')]
    return rel.strip('/').lower() or 'accueil'


def classe_page(rel):
    s = slug(rel)
    dernier = s.split('/')[-1]
    if s == 'accueil':
        return 'principale'
    if any(t in dernier for t in TECHNIQUES):
        return 'technique'
    if dernier in SECONDAIRES:
        return 'secondaire'
    return 'principale'


def normaliser(u):
    """Compare des URLs en ignorant le slash final et la casse de l'hote."""
    if not u:
        return ''
    u = u.strip()
    m = re.match(r'(?i)^(https?)://([^/]+)(.*)$', u)
    if not m:
        return u.rstrip('/')
    protocole, hote, chemin = m.group(1).lower(), m.group(2).lower(), m.group(3)
    chemin = (chemin or '/').split('#')[0]
    if not chemin.startswith('/'):
        chemin = '/' + chemin
    if chemin != '/' and chemin.endswith('/'):
        chemin = chemin[:-1]
    return f"{protocole}://{hote}{chemin}"


HOTES_INTERDITS = ('localhost', '127.0.0.1', '0.0.0.0', '.lovable.app',
                   '.vercel.app', '.netlify.app', '.github.io', 'example.com')


def hote_interdit(u):
    if not u:
        return None
    m = re.match(r'(?i)^https?://([^/]+)', u.strip())
    hote = m.group(1).lower() if m else u.lower()
    for mauvais in HOTES_INTERDITS:
        if hote == mauvais.lstrip('.') or hote.endswith(mauvais):
            return hote
    return None


def echapper_xml(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace("'", '&apos;'))
