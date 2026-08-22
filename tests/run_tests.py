#!/usr/bin/env python3
"""Banc de test du moteur MW Agency.

Chaque scenario construit un vrai site de test, execute les vrais scripts,
et verifie le resultat. Aucun mock : ce sont les scripts de production.
"""
import json, os, shutil, subprocess, sys, tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(RACINE, 'scripts')
EXEMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exemples')
os.makedirs(EXEMPLES, exist_ok=True)
DOMAINE = "https://testmwagency.ch"


def exemple(nom):
    return os.path.join(EXEMPLES, nom)

resultats = []


def page(titre="Konstructa — Showroom d'aménagement intérieur à Genève",
         canonical=None, lang="fr", texte=900, h1="Aménagement intérieur à Genève",
         schema=None, noindex=False, og_image=True, og_url=None, desc=None):
    corps = ("Konstructa accompagne les projets d'amenagement interieur haut de gamme "
             "depuis son showroom genevois. ") * max(1, texte // 100)
    d = desc if desc is not None else (
        "Showroom genevois de matieres et d'amenagement interieur haut de gamme : "
        "parquet, dressing, portes, fenetres et lumiere architecturale.")
    t = [f'<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">',
         f'<title>{titre}</title>', f'<meta name="description" content="{d}">']
    if canonical:
        t.append(f'<link rel="canonical" href="{canonical}">')
    if noindex:
        t.append('<meta name="robots" content="noindex,nofollow">')
    t.append(f'<meta property="og:title" content="{titre}">')
    t.append(f'<meta property="og:description" content="{d}">')
    if og_image:
        t.append(f'<meta property="og:image" content="{DOMAINE}/og.jpg">')
    if og_url:
        t.append(f'<meta property="og:url" content="{og_url}">')
    if schema:
        t.append('<script type="application/ld+json">' + json.dumps(schema) + '</script>')
    t.append('</head><body><header><nav>Accueil Services Contact</nav></header>')
    t.append(f'<main><h1>{h1}</h1><p>{corps[:texte]}</p>'
             '<img src="/a.jpg" alt="Showroom"></main>')
    t.append('<footer>MW Agency</footer></body></html>')
    return "\n".join(t)


def ecrire_marqueur(dossier, domaine, depot):
    chemin = os.path.join(dossier, 'marqueur-distant.json')
    json.dump({"domain": domaine, "repository": depot}, open(chemin, 'w'))
    return chemin


def faux_backup(dossier, domaine, depot):
    b = os.path.join(dossier, 'sauvegarde')
    os.makedirs(b, exist_ok=True)
    open(os.path.join(b, 'index.html'), 'w').write('<html><body>site</body></html>')
    if domaine:
        json.dump({"domain": domaine, "repository": depot},
                  open(os.path.join(b, '.mw-site.json'), 'w'))
    return b

SCHEMA = {"@context": "https://schema.org", "@type": "LocalBusiness",
          "name": "Konstructa", "telephone": "+41 22 000 00 00",
          "address": {"@type": "PostalAddress", "addressLocality": "Geneve",
                      "addressCountry": "CH"}}


def site(base, pages):
    for chemin, contenu in pages.items():
        p = os.path.join(base, chemin)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'w', encoding='utf-8').write(contenu)


DELAI_MAX = 15   # secondes : un script bloque doit faire echouer son scenario


class Bloque:
    """Resultat de substitution quand un script depasse le delai."""
    def __init__(self, script):
        self.returncode = -1
        self.stdout = f"[DELAI DEPASSE] {script} n'a pas rendu la main en {DELAI_MAX}s"
        self.stderr = self.stdout
        self.timeout = True


def lancer(script, *args, rapport=None, env=None, delai=DELAI_MAX):
    e = dict(os.environ, PYTHONPATH=SCRIPTS)
    if rapport:
        e['MW_REPORT'] = rapport
    if env:
        e.update(env)
    try:
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                           capture_output=True, text=True, env=e, timeout=delai)
        r.timeout = False
        return r
    except subprocess.TimeoutExpired:
        bloques.append(script)
        print(f"        [DELAI DEPASSE] {script} > {delai}s")
        return Bloque(script)


bloques = []


def rapport_neuf(d):
    p = os.path.join(d, 'mw-report.json')
    if os.path.exists(p):
        os.remove(p)
    return p


def lire(p):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def verifier(numero, nom, condition, detail=""):
    if bloques:
        condition = False
        detail = f"script(s) bloque(s) : {', '.join(sorted(set(bloques)))}"
        bloques.clear()
    resultats.append((numero, nom, condition, detail))
    print(f"{'  OK  ' if condition else ' ECHEC'} Test {numero} — {nom}")
    if detail and not condition:
        print("        ", detail)


# ============================================================ 1 et 2
for num, dossier in ((1, 'dist/client'), (2, 'dist')):
    with tempfile.TemporaryDirectory() as d:
        site(d, {f'{dossier}/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA)})
        rp = rapport_neuf(d)
        r = lancer('resolve_build_dir.py', d, '', rapport=rp)
        detecte = lire(rp).get('buildDir')
        verifier(num, f"Detection automatique du build dans {dossier}",
                 r.returncode == 0 and detecte == dossier,
                 f"detecte={detecte} sortie={r.returncode}")

# ---- variante : aucun build exploitable
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, 'dist'))
    open(os.path.join(d, 'dist', 'app.js'), 'w').write("console.log(1)")
    rp = rapport_neuf(d)
    r = lancer('resolve_build_dir.py', d, '', rapport=rp)
    rep = lire(rp)
    verifier('2b', "Aucun build exploitable : publication bloquee",
             r.returncode == 1 and rep.get('status_global') == 'blocked',
             f"sortie={r.returncode} etat={rep.get('status_global')}")

# ============================================================ 3
for mode, doit_bloquer in (('rapport', False), ('strict', True)):
    with tempfile.TemporaryDirectory() as d:
        b = os.path.join(d, 'dist')
        site(d, {'dist/index.html': page(
            canonical="https://maquette-client.lovable.app/", schema=SCHEMA)})
        rp = rapport_neuf(d)
        lancer('seo_audit.py', b, DOMAINE, 'fr', mode, 'true', rapport=rp)
        rep = lire(rp)
        bloque = rep.get('status_global') == 'blocked'
        canon = [e for e in rep['errors'] if e['type'] == 'canonical']
        verifier(f"3-{mode}", f"Canonical lovable.app en mode {mode}",
                 bool(canon) and bloque == doit_bloquer,
                 f"bloque={bloque} attendu={doit_bloquer} erreurs={len(canon)}")

# ============================================================ 4
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
        'dist/services/index.html': page(canonical=DOMAINE + '/', h1="Nos services"),
    })
    rp = rapport_neuf(d)
    lancer('seo_audit.py', b, DOMAINE, 'fr', 'strict', 'true', rapport=rp)
    rep = lire(rp)
    faute = [e for e in rep['errors']
             if e['page'] == 'SERVICES' and e['type'] == 'canonical']
    verifier(4, "Canonical pointant vers une autre page detectee",
             bool(faute) and rep.get('status_global') == 'blocked',
             f"erreurs services={faute}")

# ============================================================ 5
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
        'dist/services/index.html': page(canonical=DOMAINE + '/services/', h1="Services"),
        'dist/404.html': page(titre="Page introuvable", texte=40, h1="404"),
        'dist/merci/index.html': page(titre="Merci", texte=60, h1="Merci"),
        'dist/promo/index.html': page(canonical=DOMAINE + '/promo/', noindex=True, h1="Promo"),
    })
    rp = rapport_neuf(d)
    lancer('generate_sitemap.py', b, DOMAINE, rapport=rp)
    xml = open(os.path.join(b, 'sitemap.xml'), encoding='utf-8').read()
    verifier(5, "Sitemap : 404, merci et noindex exclus",
             '/404' not in xml and '/merci' not in xml and '/promo' not in xml
             and f'{DOMAINE}/' in xml and f'{DOMAINE}/services/' in xml,
             xml)

# ============================================================ 6
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
        'dist/vieux/index.html': page(canonical="https://ancien-domaine.ch/vieux/", h1="Vieux"),
        'dist/dev/index.html': page(canonical="http://localhost:3000/dev/", h1="Dev"),
    })
    rp = rapport_neuf(d)
    lancer('generate_sitemap.py', b, DOMAINE, rapport=rp)
    xml = open(os.path.join(b, 'sitemap.xml'), encoding='utf-8').read()
    import re as _re
    hotes = set(_re.findall(r'<loc>https?://([^/<]+)', xml))
    verifier(6, "Sitemap : aucune URL hors du domaine final",
             hotes == {'testmwagency.ch'}, f"hotes trouves={hotes}")

# ============================================================ 7
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {'dist/index.html':
             '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
             '<title>Maquette Konstructa</title>'
             '<meta name="description" content="Showroom genevois de matieres et '
             'd amenagement interieur haut de gamme a Geneve pour vos projets.">'
             f'<link rel="canonical" href="{DOMAINE}/">'
             '<meta property="og:title" content="K"><meta property="og:description" content="K">'
             f'<meta property="og:image" content="{DOMAINE}/og.jpg">'
             '<script type="application/ld+json">' + json.dumps(SCHEMA) + '</script>'
             '</head><body><div class="min-h-screen"></div>'
             '<script src="/assets/app.js"></script></body></html>'})
    rp = rapport_neuf(d)
    lancer('seo_audit.py', b, DOMAINE, 'fr', 'strict', 'true', rapport=rp)
    rep = lire(rp)
    vide = [e for e in rep['errors'] if e['type'] == 'html-vide']
    verifier(7, "Accueil quasi vide : publication bloquee",
             bool(vide) and rep.get('status_global') == 'blocked',
             vide[0]['message'] if vide else "aucune erreur html-vide")

# ============================================================ 8
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
        'dist/contact/index.html': page(canonical=DOMAINE + '/contact/',
                                        h1="Contact", texte=180,
                                        titre="Contact — Konstructa Geneve"),
    })
    rp = rapport_neuf(d)
    lancer('seo_audit.py', b, DOMAINE, 'fr', 'strict', 'true', rapport=rp)
    rep = lire(rp)
    bloq_contact = [e for e in rep['errors'] if e['page'] == 'CONTACT']
    verifier(8, "Page contact courte : pas de blocage",
             not bloq_contact and rep.get('status_global') != 'blocked',
             f"erreurs contact={bloq_contact} etat={rep.get('status_global')}")

# ============================================================ 9
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
        'dist/services/index.html': page(canonical=DOMAINE + '/services/', h1="Services"),
        'dist/mentions/index.html': page(canonical=DOMAINE + '/mentions/',
                                         h1="Mentions", texte=300,
                                         titre="Mentions legales — Konstructa"),
    })
    rp = rapport_neuf(d)
    lancer('seo_audit.py', b, DOMAINE, 'fr', 'strict', 'true', rapport=rp)
    rep = lire(rp)
    verifier(9, "Schema entreprise sur l'accueil seulement : site accepte",
             rep.get('status_global') != 'blocked',
             json.dumps(rep.get('errors'), ensure_ascii=False))

# ============================================================ 10
# (couvert plus bas par la serie 'identite' : voir tests 10, 10b, 15 et 16)

# ============================================================ 11
with tempfile.TemporaryDirectory() as d:
    rp = rapport_neuf(d)
    lancer('record.py', 'domain', DOMAINE, rapport=rp)
    lancer('record.py', 'backup', 'failed', '--bloquant',
           '--page', 'SAUVEGARDE', '--type', 'backup',
           '--message', "Le site en ligne contient des fichiers mais la sauvegarde a echoue.",
           '--action', "Le site livre n est pas remplace sans filet de securite.",
           rapport=rp)
    rep = lire(rp)
    verifier(11, "Sauvegarde en echec sur site livre : publication bloquee",
             rep.get('status_global') == 'blocked' and rep.get('backup') == 'failed')

    # meme situation en chantier : simple avertissement
    rp2 = rapport_neuf(d)
    lancer('record.py', 'backup', 'failed', '--avertissement',
           '--page', 'SAUVEGARDE', '--type', 'backup',
           '--message', "La sauvegarde a echoue (site en chantier).", rapport=rp2)
    rep2 = lire(rp2)
    verifier('11b', "Sauvegarde en echec en chantier : publication autorisee",
             rep2.get('status_global') != 'blocked' and len(rep2['warnings']) == 1)

# ============================================================ 12
with tempfile.TemporaryDirectory() as d:
    rp = rapport_neuf(d)
    for args in (('domain', DOMAINE), ('status', 'livre'), ('build', 'ok'),
                 ('identity', 'ok'), ('seo', 'ok'), ('backup', 'ok'), ('deploy', 'ok')):
        lancer('record.py', *args, rapport=rp)
    lancer('record.py', 'productionCheck', 'failed',
           '--page', 'PRODUCTION', '--type', 'production',
           '--message', "Le site ne repond pas correctement apres le transfert : "
                        "la page d'accueil repond 500.",
           '--action', "Une restauration automatique va etre tentee.", rapport=rp)
    lancer('record.py', 'rollback', 'done', rapport=rp)
    rep = lire(rp); rep['rollbackCheck'] = 'ok'; rep['published'] = False
    json.dump(rep, open(rp, 'w'))
    r = lancer('deployment_report.py', d, rapport=rp)
    sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    verifier(12, "Controle production en echec : rollback et email d'annulation",
             "Nouvelle version annulée" in sujet
             and "restauree automatiquement" in corps
             and "Rollback : OK" in corps, sujet)
    open(exemple('email-rollback.txt'), 'w', encoding='utf-8').write(sujet + "\n\n" + corps)

    # rollback impossible
    rp2 = rapport_neuf(d)
    for args in (('domain', DOMAINE), ('deploy', 'ok')):
        lancer('record.py', *args, rapport=rp2)
    lancer('record.py', 'productionCheck', 'failed', '--page', 'PRODUCTION',
           '--type', 'production', '--message', "Le site ne repond pas.", rapport=rp2)
    lancer('record.py', 'rollback', 'impossible', rapport=rp2)
    lancer('deployment_report.py', d, rapport=rp2)
    c2 = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    verifier('12b', "Aucune sauvegarde : le rollback n'est pas pretendu",
             "ROLLBACK IMPOSSIBLE" in c2 and "restauree automatiquement" not in c2)

# ============================================================ 13
with tempfile.TemporaryDirectory() as d:
    rp = rapport_neuf(d)
    for args in (('domain', DOMAINE), ('status', 'livre'), ('build', 'ok'),
                 ('identity', 'ok'), ('seo', 'ok'), ('backup', 'ok'),
                 ('deploy', 'ok'), ('productionCheck', 'ok')):
        lancer('record.py', *args, rapport=rp)
    rep = lire(rp); rep['published'] = True; json.dump(rep, open(rp, 'w'))
    lancer('deployment_report.py', d, rapport=rp)
    sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    r = lancer('verdict.py', rapport=rp)
    verifier(13, "Publication reussie : email de succes et workflow vert",
             "Site publié" in sujet and "SITE PUBLIE" in corps
             and r.returncode == 0, f"{sujet} / sortie verdict={r.returncode}")
    open(exemple('email-succes.txt'), 'w', encoding='utf-8').write(sujet + "\n\n" + corps)

# ---- exemple d'email de blocage, pour la documentation
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical="https://maquette-client.lovable.app/",
                                schema=SCHEMA, texte=900),
        'dist/services/index.html':
            '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
            '<title>Services — Konstructa</title>'
            '<meta name="description" content="Nos services d amenagement interieur '
            'sur mesure a Geneve : conception, selection et pose.">'
            f'<link rel="canonical" href="{DOMAINE}/services/">'
            '<meta property="og:title" content="S"><meta property="og:description" content="S">'
            f'<meta property="og:image" content="{DOMAINE}/og.jpg">'
            '</head><body><main></main><script src="/a.js"></script></body></html>',
    })
    rp = rapport_neuf(d)
    lancer('record.py', 'domain', DOMAINE, rapport=rp)
    lancer('record.py', 'build', 'ok', rapport=rp)
    lancer('generate_sitemap.py', b, DOMAINE, rapport=rp)
    lancer('seo_audit.py', b, DOMAINE, 'fr', 'strict', 'true', rapport=rp)
    lancer('deployment_report.py', d, rapport=rp)
    sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    verifier('14', "Email de blocage : contient le prompt pour Lovable",
             "Publication bloquée" in sujet and "PROMPT A DONNER A LOVABLE" in corps)
    open(exemple('email-blocage.txt'), 'w', encoding='utf-8').write(sujet + "\n\n" + corps)
    shutil.copy(os.path.join(d, 'mw-summary.md'), exemple('resume-github.md'))


# ============================================================ 15 — identite
def identite(nom_test, args, attendu, numero):
    with tempfile.TemporaryDirectory() as d:
        rp = rapport_neuf(d)
        marqueur = args.get('marqueur', 'aucun')
        if marqueur == 'fichier':
            marqueur = os.path.join(d, 'distant.json')
            json.dump(args['contenu'], open(marqueur, 'w'))
        elif marqueur == 'illisible':
            marqueur = os.path.join(d, 'distant.json')
            open(marqueur, 'w').write('{ ceci n est pas du json')
        appel = ['verifier',
                 '--connexion', args.get('connexion', 'ok'),
                 '--parent', args.get('parent', 'ok'),
                 '--dossier', args.get('dossier', 'existe'),
                 '--vide', args.get('vide', 'non'),
                 '--marqueur', marqueur,
                 '--domaine', 'https://konstructa.ch',
                 '--depot', 'MWagency2022/konstructa']
        if args.get('adopter'):
            appel.append('--adopter')
        lancer('site_identity.py', *appel, rapport=rp)
        rep = lire(rp)
        bloque_attendu = attendu not in ('nouveau', 'ok', 'adopte')
        verifier(numero, nom_test,
                 rep.get('identity') == attendu
                 and (rep.get('status_global') == 'blocked') == bloque_attendu,
                 f"identity={rep.get('identity')} etat={rep.get('status_global')}")


identite("Connexion FTP impossible : publication bloquee",
         {'connexion': 'erreur'}, 'erreur-connexion', 15)
identite("Marqueur present mais illisible : publication bloquee",
         {'marqueur': 'erreur'}, 'erreur-lecture', '15b')
identite("Marqueur mal forme : publication bloquee",
         {'marqueur': 'illisible'}, 'erreur-lecture', '15c')
identite("Dossier non vide sans marqueur : publication bloquee",
         {'vide': 'non', 'marqueur': 'aucun'}, 'non-marque', 16)
identite("Dossier vide sans marqueur : premier deploiement autorise",
         {'vide': 'oui', 'marqueur': 'aucun'}, 'nouveau', '16b')
identite("Dossier inexistant : premier deploiement autorise",
         {'dossier': 'absent'}, 'nouveau', '16c')
identite("Dossier non vide adopte explicitement",
         {'vide': 'non', 'marqueur': 'aucun', 'adopter': True}, 'adopte', '16d')
identite("Dossier FTP appartenant a un autre client : refus",
         {'marqueur': 'fichier',
          'contenu': {"domain": "https://kreon.ch", "repository": "MWagency2022/kreon"}},
         'conflit', 10)
identite("Dossier FTP conforme : publication autorisee",
         {'marqueur': 'fichier',
          'contenu': {"domain": "https://konstructa.ch", "repository": "MWagency2022/konstructa"}},
         'ok', '10b')

# ============================================================ 17 — pages attendues
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
        'dist/contact/index.html': page(canonical=DOMAINE + '/contact/', h1="Contact",
                                        texte=300, titre="Contact — Konstructa Geneve"),
    })
    json.dump({"domain": DOMAINE, "language": "fr", "status": "livre",
               "localBusiness": True,
               "pages": ["/", "/services/", "/contact/"]},
              open(os.path.join(d, 'mw-config.json'), 'w'))
    rp = rapport_neuf(d)
    lancer('generate_sitemap.py', b, DOMAINE, rapport=rp)
    lancer('check_expected_pages.py', d, b, DOMAINE, 'strict', rapport=rp)
    rep = lire(rp)
    manquante = [e for e in rep['errors'] if e['type'] == 'page-manquante']
    verifier(17, "Page attendue absente du build : publication bloquee",
             len(manquante) == 1 and 'SERVICES' == manquante[0]['page']
             and rep.get('status_global') == 'blocked',
             json.dumps(manquante, ensure_ascii=False))

with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
        'dist/services/index.html':
            '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
            '<title>Services — Konstructa</title>'
            f'<link rel="canonical" href="{DOMAINE}/services/">'
            '</head><body><main></main><script src="/a.js"></script></body></html>',
    })
    json.dump({"domain": DOMAINE, "language": "fr", "status": "livre",
               "localBusiness": True, "pages": ["/", "/services/"]},
              open(os.path.join(d, 'mw-config.json'), 'w'))
    rp = rapport_neuf(d)
    lancer('generate_sitemap.py', b, DOMAINE, rapport=rp)
    lancer('check_expected_pages.py', d, b, DOMAINE, 'strict', rapport=rp)
    rep = lire(rp)
    vide = [e for e in rep['errors'] if e['type'] == 'html-vide' and e['page'] == 'SERVICES']
    verifier('17b', "Page attendue produite mais vide : publication bloquee",
             bool(vide) and rep.get('status_global') == 'blocked')

with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    site(d, {
        'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
        'dist/services/index.html': page(canonical=DOMAINE + '/services/',
                                         h1="Services", titre="Nos services — Konstructa"),
    })
    json.dump({"domain": DOMAINE, "language": "fr", "status": "livre",
               "localBusiness": True, "pages": ["/", "/services/"]},
              open(os.path.join(d, 'mw-config.json'), 'w'))
    rp = rapport_neuf(d)
    lancer('generate_sitemap.py', b, DOMAINE, rapport=rp)
    lancer('check_expected_pages.py', d, b, DOMAINE, 'strict', rapport=rp)
    rep = lire(rp)
    verifier('17c', "Toutes les pages attendues presentes et indexees : site accepte",
             rep.get('status_global') != 'blocked',
             json.dumps(rep.get('errors'), ensure_ascii=False))

# ============================================================ 18 — transfert interrompu
with tempfile.TemporaryDirectory() as d:
    rp = rapport_neuf(d)
    for args in (('domain', DOMAINE), ('status', 'livre'), ('build', 'ok'),
                 ('identity', 'ok'), ('seo', 'ok'), ('backup', 'ok')):
        lancer('record.py', *args, rapport=rp)
    lancer('record.py', 'deploy', 'failed', '--page', 'TRANSFERT', '--type', 'ftp',
           '--message', "Le transfert des fichiers a echoue en cours de route.",
           '--action', "Une restauration automatique est tentee.", rapport=rp)
    lancer('record.py', 'rollback', 'done', rapport=rp)
    rep = lire(rp); rep['rollbackCheck'] = 'ok'; json.dump(rep, open(rp, 'w'))
    lancer('deployment_report.py', d, rapport=rp)
    sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    verifier(18, "Transfert FTP interrompu : rollback et email dedie",
             "Transfert interrompu" in sujet
             and "transfert des fichiers a echoue en cours de route" in corps
             and "Rollback : OK" in corps, sujet)
    open(exemple('email-transfert-interrompu.txt'), 'w', encoding='utf-8').write(sujet + "\n\n" + corps)

with tempfile.TemporaryDirectory() as d:
    rp = rapport_neuf(d)
    lancer('record.py', 'domain', DOMAINE, rapport=rp)
    lancer('record.py', 'deploy', 'failed', '--page', 'TRANSFERT', '--type', 'ftp',
           '--message', "Le transfert des fichiers a echoue en cours de route.", rapport=rp)
    lancer('record.py', 'rollback', 'impossible', rapport=rp)
    lancer('deployment_report.py', d, rapport=rp)
    sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    r = lancer('verdict.py', rapport=rp)
    verifier('18b', "Transfert interrompu sans sauvegarde : alerte critique",
             "ALERTE CRITIQUE" in corps and "ROLLBACK IMPOSSIBLE" in corps
             and r.returncode == 1, sujet)

# ============================================================ 19 — petites verifications
with tempfile.TemporaryDirectory() as d:
    b = os.path.join(d, 'dist')
    commun = dict(titre="Konstructa — Showroom d'amenagement interieur a Geneve")
    p1 = page(canonical=DOMAINE + '/', schema=SCHEMA, **commun)
    p2 = page(canonical=DOMAINE + '/services/', h1="Services", **commun)
    p2 = p2.replace('<img src="/a.jpg" alt="Showroom">', '<img src="/b.jpg">')
    site(d, {'dist/index.html': p1, 'dist/services/index.html': p2})
    rp = rapport_neuf(d)
    lancer('seo_audit.py', b, DOMAINE, 'fr', 'strict', 'true', rapport=rp)
    rep = lire(rp)
    types = {a['type'] for a in rep['warnings']}
    verifier(19, "alt manquant, titres et descriptions identiques : avertissements seulement",
             {'alt', 'title-double', 'description-double'} <= types
             and rep.get('status_global') != 'blocked',
             f"types={sorted(types)} etat={rep.get('status_global')}")


# ============================================================ 20 — parent illisible
identite("Dossier parent illisible : publication bloquee",
         {'parent': 'erreur'}, 'erreur-parent', 20)
identite("Dossier present dans le parent mais illisible : publication bloquee",
         {'dossier': 'illisible'}, 'erreur-lecture', '20b')
identite("Adoption tentee sur un marqueur d un autre client : refus maintenu",
         {'marqueur': 'fichier', 'adopter': True,
          'contenu': {"domain": "https://kreon.ch", "repository": "MWagency2022/kreon"}},
         'conflit', '20c')

# ============================================================ 21 — rollback en echec
with tempfile.TemporaryDirectory() as d:
    rp = rapport_neuf(d)
    for args in (('domain', DOMAINE), ('status', 'livre'), ('backup', 'ok')):
        lancer('record.py', *args, rapport=rp)
    lancer('record.py', 'deploy', 'failed', '--page', 'TRANSFERT', '--type', 'ftp',
           '--categorie', 'technique',
           '--message', "Le transfert des fichiers a echoue en cours de route.", rapport=rp)
    lancer('record.py', 'rollback', 'failed', '--page', 'RESTAURATION',
           '--type', 'production', '--categorie', 'technique',
           '--message', "La restauration automatique a echoue : le reenvoi a echoue.",
           '--action', "Intervention technique necessaire.", rapport=rp)
    lancer('deployment_report.py', d, rapport=rp)
    sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    r = lancer('verdict.py', rapport=rp)
    verifier(21, "Restauration en echec : alerte critique et workflow rouge",
             "Restauration échouée" in sujet
             and "ALERTE CRITIQUE" in corps
             and "restauree automatiquement" not in corps
             and r.returncode == 1, sujet)
    open(exemple('email-rollback-echoue.txt'), 'w', encoding='utf-8').write(sujet + "\n\n" + corps)

# ============================================================ 22 — deux categories
with tempfile.TemporaryDirectory() as d:
    rp = rapport_neuf(d)
    lancer('record.py', 'domain', DOMAINE, rapport=rp)
    lancer('record.py', 'seo', 'failed', '--page', 'ACCUEIL', '--type', 'canonical',
           '--message', "La canonical pointe vers un domaine de developpement.",
           '--action', "Remplacer la canonical.", rapport=rp)
    lancer('record.py', 'identity', 'conflit', '--bloquant',
           '--page', 'FTP', '--type', 'identite',
           '--message', "Ce dossier distant appartient a https://kreon.ch.",
           '--action', "Corriger SFTP_REMOTE_PATH.", rapport=rp)
    lancer('deployment_report.py', d, rapport=rp)
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    prompt = corps.split("PROMPT A DONNER A LOVABLE")[-1]
    verifier(22, "Problemes separes : Lovable d un cote, technique de l autre",
             "A CORRIGER DANS LOVABLE" in corps
             and "INTERVENTION TECHNIQUE" in corps
             and "canonical" in prompt
             and "SFTP_REMOTE_PATH" not in prompt,
             "le prompt Lovable ne doit pas contenir de probleme d infrastructure")
    open(exemple('email-deux-categories.txt'), 'w', encoding='utf-8').write(corps)

with tempfile.TemporaryDirectory() as d:
    rp = rapport_neuf(d)
    lancer('record.py', 'domain', DOMAINE, rapport=rp)
    lancer('record.py', 'backup', 'failed', '--bloquant',
           '--page', 'SAUVEGARDE', '--type', 'backup', '--categorie', 'technique',
           '--message', "Impossible de lire la version en ligne pour la sauvegarder.",
           '--action', "Verifier les identifiants FTP.", rapport=rp)
    lancer('deployment_report.py', d, rapport=rp)
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    verifier('22b', "Probleme purement technique : aucun prompt Lovable propose",
             "PROMPT A DONNER A LOVABLE" not in corps
             and "relevent de l'infrastructure" in corps
             and "INTERVENTION TECHNIQUE" in corps)

# ============================================================ 23 — erreur de build
with tempfile.TemporaryDirectory() as d:
    log = os.path.join(d, 'build.log')
    open(log, 'w', encoding='utf-8').write(
        "npm notice\n"
        "npm WARN deprecated inflight@1.0.6: unsupported\n"
        "added 412 packages in 9s\n"
        "found 0 vulnerabilities\n"
        "> vite build\n"
        "NPM_TOKEN=ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345\n"
        "registry=https://utilisateur:motdepasse@registry.exemple.ch\n"
        "src/routes/index.tsx (42:8): \"Boutton\" is not exported by button.tsx\n"
        "error during build:\n"
        "Error: Module not found: Can't resolve './components/Hero'\n")
    rp = rapport_neuf(d)
    lancer('record.py', 'domain', DOMAINE, rapport=rp)
    lancer('build_error.py', log, 'build', rapport=rp)
    lancer('deployment_report.py', d, rapport=rp)
    rep = lire(rp)
    sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
    corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
    verifier(23, "Erreur de build lisible dans l email, sans ouvrir GitHub",
             "Build bloqué" in sujet
             and "ERREUR DE BUILD" in corps
             and "Module not found" in corps
             and "PROMPT A DONNER A LOVABLE" in corps
             and rep.get('status_global') == 'blocked', sujet)
    verifier('23b', "Aucun secret recopie dans le rapport",
             "ghp_AbCdEf" not in corps and "motdepasse" not in corps
             and "***" in corps,
             "un identifiant a fuite dans le rapport")
    verifier('23c', "Bruit npm ecarte de l extrait",
             "npm WARN deprecated" not in rep.get('buildError', '')
             and "found 0 vulnerabilities" not in rep.get('buildError', ''))
    open(exemple('email-build.txt'), 'w', encoding='utf-8').write(sujet + "\n\n" + corps)

# ============================================================ 24 — timeout du banc
with tempfile.TemporaryDirectory() as d:
    lent = os.path.join(SCRIPTS, '_scenario_lent_temporaire.py')
    open(lent, 'w').write("import time\ntime.sleep(30)\n")
    try:
        r = lancer('_scenario_lent_temporaire.py', delai=2)
        depasse = getattr(r, 'timeout', False) and r.returncode == -1
        bloques.clear()   # ce depassement est attendu : il ne doit pas polluer le verdict
        verifier(24, "Un script bloque fait echouer son scenario", depasse,
                 f"timeout={getattr(r, 'timeout', None)} code={r.returncode}")
    finally:
        os.remove(lent)
        bloques.clear()


# ============================================================ 25 — restauration : dossier cible
def restauration(numero, nom_test, prepare, attendu_bloque, verif=None):
    """Scenario de restauration : on pilote le rapport comme le fait le
    workflow, puis on controle le rapport, l email et le verdict."""
    with tempfile.TemporaryDirectory() as d:
        rp = rapport_neuf(d)
        lancer('record.py', 'domain', DOMAINE, rapport=rp)
        lancer('record.py', 'status', 'livre', rapport=rp)
        rep = lire(rp)
        rep.update(operation='restauration', restoreBackup='2026-08-20_1430_abc1234',
                   revert='none', restore='not_started', safetyNet='not_started',
                   backupIdentity='not_started')
        json.dump(rep, open(rp, 'w'))
        prepare(d, rp)
        lancer('deployment_report.py', d, rapport=rp)
        rep = lire(rp)
        sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
        corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
        r = lancer('verdict.py', rapport=rp)
        bloque = rep.get('status_global') == 'blocked'
        ok = bloque == attendu_bloque
        detail = f"bloque={bloque} sujet={sujet}"
        if verif:
            supplement = verif(rep, sujet, corps, r)
            ok = ok and supplement
        verifier(numero, nom_test, ok, detail)
        return d, sujet, corps


restauration(25, "Restauration vers un dossier marque autre client : refus avant ecriture",
             lambda d, rp: lancer('site_identity.py', 'verifier',
                                  '--connexion', 'ok', '--parent', 'ok',
                                  '--dossier', 'existe', '--vide', 'non',
                                  '--marqueur', ecrire_marqueur(d, "https://kreon.ch",
                                                                "MWagency2022/kreon"),
                                  '--domaine', DOMAINE, '--depot', 'MWagency2022/test-auto-dist',
                                  rapport=rp),
             True,
             lambda rep, sujet, corps, r: (rep.get('identity') == 'conflit'
                                           and "Restauration bloquée" in sujet
                                           and "Aucun fichier n'a ete modifie" in corps
                                           and r.returncode == 1))

restauration(26, "Restauration vers un dossier non vide sans marqueur : refus",
             lambda d, rp: lancer('site_identity.py', 'verifier',
                                  '--connexion', 'ok', '--parent', 'ok',
                                  '--dossier', 'existe', '--vide', 'non',
                                  '--marqueur', 'aucun',
                                  '--domaine', DOMAINE, '--depot', 'MWagency2022/test-auto-dist',
                                  rapport=rp),
             True,
             lambda rep, sujet, corps, r: rep.get('identity') == 'non-marque' and r.returncode == 1)

restauration(27, "Sauvegarde appartenant a un autre client : refus",
             lambda d, rp: lancer('site_identity.py', 'verifier-sauvegarde',
                                  faux_backup(d, "https://kreon.ch", "MWagency2022/kreon"),
                                  DOMAINE, 'MWagency2022/test-auto-dist',
                                  '2026-08-20_1430_abc1234', rapport=rp),
             True,
             lambda rep, sujet, corps, r: (rep.get('backupIdentity') == 'refuse'
                                           and "appartient a" in corps
                                           and r.returncode == 1))

restauration('27b', "Sauvegarde sans marqueur : refus",
             lambda d, rp: lancer('site_identity.py', 'verifier-sauvegarde',
                                  faux_backup(d, None, None),
                                  DOMAINE, 'MWagency2022/test-auto-dist',
                                  '2026-08-20_1430_abc1234', rapport=rp),
             True,
             lambda rep, sujet, corps, r: rep.get('backupIdentity') == 'refuse')

restauration(28, "Filet de securite impossible : la restauration ne commence pas",
             lambda d, rp: lancer('record.py', 'safetyNet', 'failed', '--bloquant',
                                  '--page', 'FILET', '--type', 'backup',
                                  '--categorie', 'technique',
                                  '--message', "La version actuellement en ligne n a pas pu etre sauvegardee.",
                                  '--action', "Aucun fichier n a ete ecrase.", rapport=rp),
             True,
             lambda rep, sujet, corps, r: (rep.get('restore') == 'not_started'
                                           and "Restauration bloquée" in sujet
                                           and r.returncode == 1))


def transfert_interrompu(d, rp):
    lancer('record.py', 'identity', 'ok', rapport=rp)
    lancer('record.py', 'backupIdentity', 'ok', rapport=rp)
    lancer('record.py', 'safetyNet', 'ok', rapport=rp)
    lancer('record.py', 'restore', 'failed', '--page', 'RESTAURATION', '--type', 'ftp',
           '--categorie', 'technique',
           '--message', "Le transfert de restauration a echoue en cours de route.",
           rapport=rp)
    lancer('record.py', 'revert', 'done', rapport=rp)
    rep = lire(rp); rep['revertCheck'] = 'ok'; json.dump(rep, open(rp, 'w'))


restauration(29, "Transfert de restauration interrompu : retour arriere et workflow rouge",
             transfert_interrompu, False,
             lambda rep, sujet, corps, r: ("Restauration annulée" in sujet
                                           and "remis" in corps
                                           and r.returncode == 1))


def production_ko_retour_ok(d, rp):
    for c in ('identity', 'backupIdentity', 'safetyNet'):
        lancer('record.py', c, 'ok', rapport=rp)
    lancer('record.py', 'restore', 'ok', rapport=rp)
    lancer('record.py', 'productionCheck', 'failed',
           '--page', 'PRODUCTION', '--type', 'production', '--categorie', 'technique',
           '--message', "La version restauree ne repond pas correctement.", rapport=rp)
    lancer('record.py', 'revert', 'done', rapport=rp)
    rep = lire(rp); rep['revertCheck'] = 'ok'; json.dump(rep, open(rp, 'w'))


restauration(30, "Restauration non fonctionnelle : retour automatique a l etat precedent",
             production_ko_retour_ok, False,
             lambda rep, sujet, corps, r: ("Restauration annulée" in sujet
                                           and "n'etait pas fonctionnelle" in corps
                                           and "Site accessible : OK" in corps
                                           and r.returncode == 1))


def retour_echoue(d, rp):
    for c in ('identity', 'backupIdentity', 'safetyNet'):
        lancer('record.py', c, 'ok', rapport=rp)
    lancer('record.py', 'restore', 'ok', rapport=rp)
    lancer('record.py', 'revert', 'failed', '--page', 'RETOUR', '--type', 'production',
           '--categorie', 'technique',
           '--message', "La restauration et le retour arriere ont echoue.",
           '--action', "Intervention technique necessaire.", rapport=rp)


restauration(31, "Retour arriere en echec : alerte critique",
             retour_echoue, False,
             lambda rep, sujet, corps, r: ("Restauration et retour arrière échoués" in sujet
                                           and "Intervention technique" in corps
                                           and r.returncode == 1))


def restauration_reussie(d, rp):
    for c in ('identity', 'backupIdentity', 'safetyNet'):
        lancer('record.py', c, 'ok', rapport=rp)
    lancer('record.py', 'restore', 'ok', rapport=rp)
    lancer('record.py', 'productionCheck', 'ok', rapport=rp)


d31, s31, c31 = restauration(32, "Restauration reussie : email de succes et workflow vert",
                             restauration_reussie, False,
                             lambda rep, sujet, corps, r: ("Restauration réussie" in sujet
                                                           and "2026-08-20_1430_abc1234" in corps
                                                           and r.returncode == 0))

# ============================================================ 33 — domaine et statut livre
def config_livre(numero, nom_test, domaine, doit_bloquer, statut='livre'):
    with tempfile.TemporaryDirectory() as d:
        cfg = {"language": "fr", "status": statut, "localBusiness": True}
        if domaine is not None:
            cfg["domain"] = domaine
        json.dump(cfg, open(os.path.join(d, 'mw-config.json'), 'w'))
        rp = rapport_neuf(d)
        r = lancer('resolve_config.py', d, rapport=rp)
        rep = lire(rp)
        bloque = rep.get('status_global') == 'blocked' or r.returncode != 0
        verifier(numero, nom_test, bloque == doit_bloquer,
                 f"bloque={bloque} sortie={r.returncode}")


config_livre(33, "Site livre sans domaine : publication bloquee", None, True)
config_livre('33b', "Site livre avec domaine vide : publication bloquee", "", True)
config_livre(34, "Site livre en HTTP : publication bloquee", "http://client.ch", True)
config_livre('34b', "Site livre sur une adresse lovable.app : publication bloquee",
             "https://maquette.lovable.app", True)
config_livre('34c', "Site livre avec domaine HTTPS valide : accepte",
             "https://client.ch", False)
config_livre('34d', "Site en chantier sans domaine : simple avertissement",
             None, False, statut='chantier')

# ============================================================ 35 — page declaree mais noindex
def page_noindex(numero, nom_test, mode, doit_bloquer):
    with tempfile.TemporaryDirectory() as d:
        b = os.path.join(d, 'dist')
        site(d, {
            'dist/index.html': page(canonical=DOMAINE + '/', schema=SCHEMA),
            'dist/services/index.html': page(canonical=DOMAINE + '/services/',
                                             h1="Services", noindex=True,
                                             titre="Nos services — Konstructa"),
        })
        json.dump({"domain": DOMAINE, "language": "fr",
                   "status": "livre" if mode == 'strict' else "chantier",
                   "localBusiness": True, "pages": ["/", "/services/"]},
                  open(os.path.join(d, 'mw-config.json'), 'w'))
        rp = rapport_neuf(d)
        lancer('generate_sitemap.py', b, DOMAINE, rapport=rp)
        lancer('check_expected_pages.py', d, b, DOMAINE, mode, rapport=rp)
        rep = lire(rp)
        erreurs = [e for e in rep['errors'] if e['type'] == 'noindex-declare']
        alertes = [a for a in rep['warnings'] if a['type'] == 'noindex-declare']
        bloque = rep.get('status_global') == 'blocked'
        signale = bool(erreurs) if doit_bloquer else bool(alertes)
        verifier(numero, nom_test, signale and bloque == doit_bloquer,
                 f"erreurs={len(erreurs)} alertes={len(alertes)} bloque={bloque}")


page_noindex(35, "Page declaree publique mais en noindex, en strict : bloquee", 'strict', True)
page_noindex('35b', "Meme cas en chantier : avertissement seulement", 'rapport', False)


# ============================================================ 36 — backup_path
def chemin_sauvegarde(numero, nom_test, remote, bp, attendu, delete=None):
    """attendu : chemin retenu, ou None si le scenario doit bloquer."""
    with tempfile.TemporaryDirectory() as d:
        rp = rapport_neuf(d)
        env_github = os.path.join(d, 'env.txt')
        open(env_github, 'w').write('')
        lancer('resolve_backup_path.py', remote, bp, rapport=rp,
               env={'GITHUB_ENV': env_github})
        lignes = dict(l.split('=', 1) for l in open(env_github).read().splitlines() if '=' in l)
        rep = lire(rp)
        bloque = rep.get('status_global') == 'blocked'
        if attendu is None:
            ok = bloque and not lignes.get('BACKUP_ROOT')
        else:
            ok = (not bloque) and lignes.get('BACKUP_ROOT') == attendu \
                 and lignes.get('BACKUP_SAFE') == '1'
            if delete is not None:
                ok = ok and lignes.get('MIRROR_DELETE', '') == delete
        verifier(numero, nom_test, ok,
                 f"bloque={bloque} root={lignes.get('BACKUP_ROOT')} "
                 f"delete={lignes.get('MIRROR_DELETE')!r}")


chemin_sauvegarde(36, "backup_path personnalise accepte",
                  "public_html/", "sauvegardes-mw", "sauvegardes-mw", delete="--delete")
chemin_sauvegarde('36b', "Sans backup_path : chemin automatique conserve",
                  "sites/testmwagency.ch/", "", "backups/testmwagency.ch")
chemin_sauvegarde(37, "backup_path a l interieur du site : refuse",
                  "sites/x.ch", "sites/x.ch/backups", None)
chemin_sauvegarde('37b', "backup_path egal au dossier du site : refuse",
                  "sites/x.ch", "sites/x.ch", None)
chemin_sauvegarde('37c', "backup_path a la racine : refuse",
                  "public_html/", "/", None)
chemin_sauvegarde(38, "Chemin distant racine sans backup_path : refuse",
                  ".", "", None)
chemin_sauvegarde('38b', "Chemin distant racine avec backup_path externe : accepte",
                  ".", "../sauvegardes", "../sauvegardes", delete="")
chemin_sauvegarde('38c', "Chemin distant racine avec backup_path absolu : accepte",
                  ".", "/home/clients/abc/sauvegardes", "/home/clients/abc/sauvegardes")
chemin_sauvegarde('38d', "Chemin distant racine avec backup_path interne : refuse",
                  ".", "backups/x", None)


# --- deploy et restore doivent resoudre exactement le meme chemin
with tempfile.TemporaryDirectory() as d:
    import re as _re
    workflows = os.path.join(RACINE, '.github', 'workflows')
    deploy = open(os.path.join(workflows, 'static-deploy.yml'), encoding='utf-8').read()
    restore = open(os.path.join(workflows, 'static-restore.yml'), encoding='utf-8').read()

    def appel(texte):
        m = _re.search(r'resolve_backup_path\.py[^\n]*\n[^\n]*', texte)
        return _re.sub(r'\s+', ' ', m.group(0)).strip() if m else None

    a_deploy, a_restore = appel(deploy), appel(restore)
    memes_arguments = (a_deploy == a_restore
                       and a_deploy is not None
                       and 'steps.config.outputs.backup_path' in a_deploy)
    calcul_local = ('BACKUP_ROOT=backups' in deploy) or ('BACKUP_ROOT=backups' in restore)
    verifier(39, "Deploiement et restauration resolvent le meme chemin de sauvegarde",
             memes_arguments and not calcul_local,
             f"deploy={a_deploy!r} restore={a_restore!r} calcul_local={calcul_local}")

    # et le meme resultat, a l execution
    resultats_obtenus = []
    for _ in range(2):
        d2 = tempfile.mkdtemp()
        rp = os.path.join(d2, 'r.json')
        env_github = os.path.join(d2, 'env.txt')
        open(env_github, 'w').write('')
        lancer('resolve_backup_path.py', 'sites/testmwagency.ch/', '',
               rapport=rp, env={'GITHUB_ENV': env_github})
        lignes = dict(l.split('=', 1) for l in open(env_github).read().splitlines() if '=' in l)
        resultats_obtenus.append(lignes.get('BACKUP_ROOT'))
    verifier('39b', "Resolution deterministe entre deux appels",
             len(set(resultats_obtenus)) == 1 and resultats_obtenus[0] == 'backups/testmwagency.ch',
             str(resultats_obtenus))


# ============================================================ 40 — erreurs de configuration
def config_invalide(numero, nom_test, contenu, motif_attendu):
    with tempfile.TemporaryDirectory() as d:
        chemin = os.path.join(d, 'mw-config.json')
        if isinstance(contenu, str):
            open(chemin, 'w', encoding='utf-8').write(contenu)
        else:
            json.dump(contenu, open(chemin, 'w'))
        rp = rapport_neuf(d)
        env_github = os.path.join(d, 'out.txt')
        open(env_github, 'w').write('')
        r = lancer('resolve_config.py', d, rapport=rp, env={'GITHUB_OUTPUT': env_github})
        rep = lire(rp)
        sorties = dict(l.split('=', 1) for l in open(env_github).read().splitlines() if '=' in l)

        # Le script ne doit jamais s interrompre brutalement...
        pas_de_mort_brutale = r.returncode == 0
        # ...il doit enregistrer le probleme...
        enregistre = rep.get('status_global') == 'blocked' and bool(rep.get('errors'))
        motif_present = any(motif_attendu.lower() in (e.get('message') or '').lower()
                            for e in rep.get('errors', []))
        # ...et publier des sorties sures pour que le rapport et l email marchent.
        sorties_sures = (sorties.get('notify') == 'true'
                         and 'status' in sorties and 'language' in sorties)

        # le rapport doit ensuite pouvoir etre produit
        lancer('deployment_report.py', d, rapport=rp)
        corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
        sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
        v = lancer('verdict.py', rapport=rp)

        verifier(numero, nom_test,
                 pas_de_mort_brutale and enregistre and motif_present
                 and sorties_sures and "bloquée" in sujet.lower()
                 and v.returncode == 1,
                 f"sortie={r.returncode} bloque={rep.get('status_global')} "
                 f"notify={sorties.get('notify')} verdict={v.returncode}")
        return corps


config_invalide(40, "mw-config.json invalide : rapport bloque, pas d arret brutal",
                '{ "domain": "https://x.ch", ceci n est pas du json', "illisible")
config_invalide(41, "Statut invalide : rapport bloque",
                {"domain": "https://x.ch", "status": "en-cours", "language": "fr"},
                "statut")
config_invalide(42, "Domaine invalide : rapport bloque",
                {"domain": "pas-une-url", "status": "chantier", "language": "fr"},
                "adresse valide")
config_invalide('42b', "Site livre sans domaine : rapport bloque",
                {"status": "livre", "language": "fr"}, "aucun domaine")
config_invalide('42c', "Site livre en HTTP : rapport bloque",
                {"domain": "http://client.ch", "status": "livre"}, "https")
config_invalide('42d', "Site livre sur lovable.app : rapport bloque",
                {"domain": "https://maquette.lovable.app", "status": "livre"},
                "developpement")


# --- aucune etape FTP ne peut demarrer apres une erreur de configuration
with tempfile.TemporaryDirectory() as d:
    import yaml as _yaml
    wf = _yaml.safe_load(open(os.path.join(RACINE, '.github', 'workflows',
                                           'static-deploy.yml'), encoding='utf-8'))
    etapes = wf['jobs']['publication']['steps']
    noms = [e.get('name') for e in etapes]
    i_config = noms.index('Configuration effective')

    # le gate doit etre appele des la resolution de configuration
    gate_immediat = 'gate.py' in (etapes[i_config].get('run') or '')

    # toute etape sensible apres la configuration doit etre gardee
    SENSIBLES = ('Installation de Node', 'Installation des dependances', 'Build',
                 'Installation de lftp', 'Preparation de la connexion',
                 'Emplacement des sauvegardes', 'Verification du dossier distant',
                 'Sauvegarde de la version en ligne', 'Mise en ligne',
                 'Controle de production', 'Restauration automatique')
    non_gardees = [e.get('name') for e in etapes
                   if e.get('name') in SENSIBLES
                   and "env.MW_BLOCKED != 'true'" not in str(e.get('if', ''))]
    verifier(43, "Aucune etape d installation ou FTP apres une erreur de configuration",
             gate_immediat and not non_gardees,
             f"gate_immediat={gate_immediat} non_gardees={non_gardees}")

    # le job controle doit tout de meme laisser passer pour produire le rapport
    ctrl = wf['jobs']['controle']['steps']
    decision = [e for e in ctrl if e.get('name') == 'Faut-il publier ?'][0]
    verifier('43b', "Une configuration invalide atteint quand meme le rapport",
             'MW_BLOCKED' in decision['run'] and 'publier=true' in decision['run'],
             "le job controle doit forcer la suite pour que le rapport soit produit")


# ============================================================ 44 — restauration depuis un etat vide
def restauration_etat_vide(numero, nom_test, prepare, verif):
    with tempfile.TemporaryDirectory() as d:
        rp = rapport_neuf(d)
        lancer('record.py', 'domain', DOMAINE, rapport=rp)
        lancer('record.py', 'status', 'livre', rapport=rp)
        rep = lire(rp)
        rep.update(operation='restauration', restoreBackup='2026-08-20_1430_abc1234',
                   revert='none', restore='not_started', identity='ok',
                   backupIdentity='ok', safetyNet='skipped', previousState='vide')
        json.dump(rep, open(rp, 'w'))
        prepare(d, rp)
        lancer('deployment_report.py', d, rapport=rp)
        rep = lire(rp)
        sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
        corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
        v = lancer('verdict.py', rapport=rp)
        verifier(numero, nom_test, verif(rep, sujet, corps, v), sujet)


def transfert_ko_depuis_vide(d, rp):
    lancer('record.py', 'restore', 'failed', '--page', 'RESTAURATION', '--type', 'ftp',
           '--categorie', 'technique',
           '--message', "Le transfert de restauration a echoue en cours de route.",
           rapport=rp)
    lancer('record.py', 'revert', 'done', rapport=rp)
    rep = lire(rp); rep['revertCheck'] = 'ok'; json.dump(rep, open(rp, 'w'))


restauration_etat_vide(44, "Etat initial vide + transfert interrompu : dossier revide",
                       transfert_ko_depuis_vide,
                       lambda rep, sujet, corps, v: (rep.get('previousState') == 'vide'
                                                     and rep.get('revert') == 'done'
                                                     and rep.get('revertCheck') == 'ok'
                                                     and "Restauration annulée" in sujet
                                                     and v.returncode == 1))


def production_ko_depuis_vide(d, rp):
    lancer('record.py', 'restore', 'ok', rapport=rp)
    lancer('record.py', 'productionCheck', 'failed', '--page', 'PRODUCTION',
           '--type', 'production', '--categorie', 'technique',
           '--message', "La version restauree ne repond pas correctement.", rapport=rp)
    lancer('record.py', 'revert', 'done', rapport=rp)
    rep = lire(rp); rep['revertCheck'] = 'ok'; json.dump(rep, open(rp, 'w'))


restauration_etat_vide(45, "Etat initial vide + controle production KO : dossier revide",
                       production_ko_depuis_vide,
                       lambda rep, sujet, corps, v: (rep.get('revert') == 'done'
                                                     and rep.get('revertCheck') == 'ok'
                                                     and "Restauration annulée" in sujet
                                                     and v.returncode == 1))

# --- la logique de remise a vide doit exister dans le workflow
with tempfile.TemporaryDirectory() as d:
    wf = open(os.path.join(RACINE, '.github', 'workflows', 'static-restore.yml'),
              encoding='utf-8').read()
    verifier('45b', "Le workflow memorise l etat vide et sait revider le dossier",
             'ETAT_PRECEDENT=vide' in wf
             and 'Remise a vide du dossier cible' in wf
             and 'la remise a vide du dossier a echoue' in wf
             and 'apres la remise a vide' in wf,
             "la branche de remise a vide est absente du workflow de restauration")


# ============================================================ 46 — rollback du premier deploiement
#
#  Ces scenarios executent la VRAIE etape bash du workflow, avec un faux lftp
#  qui simule les reponses du serveur. C'est la logique de production qui est
#  testee, pas une reimplementation.

def etape_rollback():
    import yaml as _y
    wf = _y.safe_load(open(os.path.join(RACINE, '.github', 'workflows',
                                        'static-deploy.yml'), encoding='utf-8'))
    st = [e for e in wf['jobs']['publication']['steps']
          if e.get('name') == 'Restauration automatique'][0]
    return st['run'].replace('${{ steps.config.outputs.domain }}', 'https://exemple.invalid')


ROLLBACK_SH = etape_rollback()


def jouer_rollback(etat, faux_lftp, remote='sites/testmwagency.ch',
                   backup_dir=None, mirror_delete='--delete',
                   nom='testmwagency.ch', parent='sites'):
    """Execute l'etape de rollback avec un faux serveur, renvoie le rapport."""
    d = tempfile.mkdtemp()
    faux = os.path.join(d, 'lftp')
    open(faux, 'w').write("#!/usr/bin/env bash\n" + faux_lftp)
    os.chmod(faux, 0o755)

    env = dict(os.environ,
               PATH=d + os.pathsep + os.environ['PATH'],
               RUNNER_TEMP=d, SCRIPTS=SCRIPTS, PYTHONPATH=SCRIPTS,
               MW_REPORT=os.path.join(d, 'mw-report.json'),
               CONNECT_FILE=os.path.join(d, 'connect.txt'),
               SFTP_REMOTE_PATH=remote, ETAT_DISTANT=etat,
               CIBLE_NOM=nom, CIBLE_PARENT=parent,
               MIRROR_DELETE=mirror_delete)
    if backup_dir:
        env['BACKUP_DIR'] = backup_dir
    else:
        env.pop('BACKUP_DIR', None)
    open(env['CONNECT_FILE'], 'w').write("open serveur\n")

    sc = os.path.join(d, 'rollback.sh')
    open(sc, 'w').write(ROLLBACK_SH)
    try:
        r = subprocess.run(['bash', sc], capture_output=True, text=True,
                           env=env, timeout=DELAI_MAX)
        sortie = r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        sortie = "[DELAI DEPASSE]"
    rep = json.load(open(env['MW_REPORT'])) if os.path.exists(env['MW_REPORT']) else {}
    return rep, sortie


# --- faux serveurs -------------------------------------------------------
LIT = 'CMD=$(cat "$2" 2>/dev/null)\n'

SERVEUR_VIDE_OK = LIT + '''
if echo "$CMD" | grep -q "mirror -R"; then exit 0; fi
if echo "$CMD" | grep -q "cls -1 -a"; then printf "./\n../\n"; exit 0; fi
exit 0'''

SERVEUR_VIDE_MIROIR_KO = LIT + '''
if echo "$CMD" | grep -q "mirror -R"; then echo "Access failed" >&2; exit 1; fi
exit 0'''

SERVEUR_VIDE_RESTE_DES_FICHIERS = LIT + '''
if echo "$CMD" | grep -q "mirror -R"; then exit 0; fi
if echo "$CMD" | grep -q "cls -1 -a"; then printf "index.html\nassets/\n"; exit 0; fi
exit 0'''

SERVEUR_ABSENT_OK = LIT + '''
if echo "$CMD" | grep -q "rm -r"; then exit 0; fi
if echo "$CMD" | grep -q "cls -1 -a"; then printf "autre-site.ch/\nvieux.ch/\n"; exit 0; fi
exit 0'''

SERVEUR_ABSENT_RM_KO = LIT + '''
if echo "$CMD" | grep -q "rm -r"; then echo "Permission denied" >&2; exit 1; fi
exit 0'''

SERVEUR_ABSENT_TOUJOURS_LA = LIT + '''
if echo "$CMD" | grep -q "rm -r"; then exit 0; fi
if echo "$CMD" | grep -q "cls -1 -a"; then printf "autre-site.ch/\ntestmwagency.ch/\n"; exit 0; fi
exit 0'''


# --- 1 et 2 : dossier initial vide --------------------------------------
rep, out = jouer_rollback('vide', SERVEUR_VIDE_OK)
verifier(46, "Dossier initial vide + echec : dossier remis vide",
         rep.get('rollback') == 'done' and rep.get('published') is False
         and rep.get('rollbackCheck') == 'ok'
         and "etat vide initial" in out,
         f"rollback={rep.get('rollback')} published={rep.get('published')}")

verifier('46b', "Remise a vide reellement verifiee par relecture du dossier",
         "cls -1 -a" in ROLLBACK_SH and "apres la remise a vide" in ROLLBACK_SH,
         "la verification par relecture est absente")

# le meme code sert pour un echec de transfert et pour un controle production KO :
# l etape est declenchee par MW_NEED_ROLLBACK ou par l echec de l etape prod.
import yaml as _yaml_cond
_wf = _yaml_cond.safe_load(open(os.path.join(RACINE, '.github', 'workflows',
                                             'static-deploy.yml'), encoding='utf-8'))
_cond = str([e for e in _wf['jobs']['publication']['steps']
             if e.get('name') == 'Restauration automatique'][0]['if'])
verifier(47, "Dossier vide + controle production KO : meme retour arriere",
         "MW_NEED_ROLLBACK == 'true'" in _cond and "steps.prod.outcome == 'failure'" in _cond,
         f"condition={_cond}")

# --- 3 et 4 : dossier initial absent -------------------------------------
rep, out = jouer_rollback('absent', SERVEUR_ABSENT_OK)
verifier(48, "Dossier initial absent + echec : dossier supprime",
         rep.get('rollback') == 'done' and rep.get('published') is False
         and rep.get('rollbackCheck') == 'ok'
         and "revenu a son etat initial" in out,
         f"rollback={rep.get('rollback')} sortie={out[-200:]}")

verifier('48b', "Absence reellement verifiee dans le dossier parent",
         "parent-apres.txt" in ROLLBACK_SH
         and "existe encore dans son parent" in ROLLBACK_SH)

rep, out = jouer_rollback('absent', SERVEUR_ABSENT_TOUJOURS_LA)
verifier(49, "Dossier encore present apres suppression : rollback=failed",
         rep.get('rollback') == 'failed'
         and "existe encore dans son parent" in out,
         f"rollback={rep.get('rollback')}")

# --- 7 : jamais supprimer une racine -------------------------------------
for racine_testee in ('.', '/', ''):
    rep, out = jouer_rollback('absent', SERVEUR_ABSENT_OK, remote=racine_testee)
    ok = rep.get('rollback') == 'failed' and "suppression interdite" in out
    verifier(f'50-{racine_testee or "vide"}',
             f"Racine \"{racine_testee or '(vide)'}\" : suppression impossible", ok,
             f"rollback={rep.get('rollback')} sortie={out[-160:]}")

# --- 8 et 9 : echecs ------------------------------------------------------
rep, out = jouer_rollback('vide', SERVEUR_VIDE_MIROIR_KO)
verifier(51, "Echec de la remise a vide : rollback=failed",
         rep.get('rollback') == 'failed' and "remise a vide" in out)

rep, out = jouer_rollback('vide', SERVEUR_VIDE_RESTE_DES_FICHIERS)
verifier('51b', "Dossier non vide apres remise a vide : rollback=failed",
         rep.get('rollback') == 'failed' and "contient encore" in out)

rep, out = jouer_rollback('absent', SERVEUR_ABSENT_RM_KO)
verifier(52, "Echec de la suppression du dossier cree : rollback=failed",
         rep.get('rollback') == 'failed' and "suppression du dossier cree a echoue" in out)

# --- 10 : plus jamais rollback=impossible faute de sauvegarde -------------
sans_sauvegarde = []
for etat, serveur in (('vide', SERVEUR_VIDE_OK), ('absent', SERVEUR_ABSENT_OK)):
    rep, _ = jouer_rollback(etat, serveur, backup_dir=None)
    sans_sauvegarde.append((etat, rep.get('rollback')))
verifier(53, "Premier deploiement : jamais rollback=impossible faute de sauvegarde",
         all(v == 'done' for _, v in sans_sauvegarde), str(sans_sauvegarde))

# un site qui avait deja des fichiers conserve l ancien comportement
rep, out = jouer_rollback('fichiers', SERVEUR_VIDE_OK, backup_dir=None)
verifier('53b', "Site existant sans sauvegarde : rollback=impossible conserve",
         rep.get('rollback') == 'impossible', f"rollback={rep.get('rollback')}")

# --- l etat distant est bien memorise avant toute ecriture ----------------
_dep = open(os.path.join(RACINE, '.github', 'workflows', 'static-deploy.yml'),
            encoding='utf-8').read()
verifier(54, "Etat du dossier memorise avant ecriture, dans GITHUB_ENV et le rapport",
         "ETAT_DISTANT=$ETAT_DISTANT" in _dep
         and "r['remoteState']" in _dep
         and _dep.index('ETAT_DISTANT=$ETAT_DISTANT') < _dep.index('- name: Sauvegarde de la version en ligne'),
         "la memorisation doit preceder la premiere ecriture")

# --- rapport : un premier deploiement annonce le bon message -------------
for etat, attendu in (('absent', 'dossier cree pendant l\'operation a ete supprime'),
                      ('vide', 'remis dans son etat vide initial')):
    with tempfile.TemporaryDirectory() as d:
        rp = rapport_neuf(d)
        lancer('record.py', 'domain', DOMAINE, rapport=rp)
        lancer('record.py', 'deploy', 'failed', '--page', 'TRANSFERT', '--type', 'ftp',
               '--categorie', 'technique', '--message', "Transfert interrompu.", rapport=rp)
        lancer('record.py', 'rollback', 'done', rapport=rp)
        rep = lire(rp); rep['remoteState'] = etat; rep['published'] = False
        json.dump(rep, open(rp, 'w'))
        lancer('deployment_report.py', d, rapport=rp)
        sujet = open(os.path.join(d, 'mw-email-subject.txt'), encoding='utf-8').read()
        corps = open(os.path.join(d, 'mw-email-body.txt'), encoding='utf-8').read()
        v = lancer('verdict.py', rapport=rp)
        verifier(f'55-{etat}',
                 f"Premier deploiement ({etat}) : email d etat initial restaure",
                 "serveur remis en état" in sujet
                 and "LA PUBLICATION A ECHOUE" in corps
                 and attendu in corps and v.returncode == 1,
                 sujet)
        if etat == 'absent':
            open(exemple('email-premier-deploiement-annule.txt'), 'w',
                 encoding='utf-8').write(sujet + "\n\n" + corps)

# ============================================================ 56 — nettoyage backup_path
_res = open(os.path.join(RACINE, '.github', 'workflows', 'static-restore.yml'),
            encoding='utf-8').read()
_cfg = open(os.path.join(SCRIPTS, 'resolve_config.py'), encoding='utf-8').read()
verifier(56, "Aucune reference a inputs.backup_path ni a IN_BACKUP_PATH",
         'inputs.backup_path' not in _dep and 'inputs.backup_path' not in _res
         and 'IN_BACKUP_PATH' not in _dep and 'IN_BACKUP_PATH' not in _res
         and 'IN_BACKUP_PATH' not in _cfg,
         "une fausse source secondaire subsiste")

with tempfile.TemporaryDirectory() as d:
    json.dump({"domain": DOMAINE, "language": "fr", "status": "chantier",
               "localBusiness": True, "backup_path": "sauvegardes-mw"},
              open(os.path.join(d, 'mw-config.json'), 'w'))
    rp = rapport_neuf(d)
    go = os.path.join(d, 'out.txt'); open(go, 'w').write('')
    lancer('resolve_config.py', d, rapport=rp, env={'GITHUB_OUTPUT': go})
    sorties = dict(l.split('=', 1) for l in open(go).read().splitlines() if '=' in l)

    chemins_obtenus = {}
    for usage in ('deploiement', 'restauration'):
        ge = os.path.join(d, f'env-{usage}.txt'); open(ge, 'w').write('')
        rp2 = os.path.join(d, f'r-{usage}.json')
        lancer('resolve_backup_path.py', 'public_html/', sorties.get('backup_path', ''),
               rapport=rp2, env={'GITHUB_ENV': ge})
        lignes = dict(l.split('=', 1) for l in open(ge).read().splitlines() if '=' in l)
        chemins_obtenus[usage] = lignes.get('BACKUP_ROOT')

    verifier(57, "backup_path de mw-config.json actif dans deploiement ET restauration",
             sorties.get('backup_path') == 'sauvegardes-mw'
             and chemins_obtenus['deploiement'] == 'sauvegardes-mw'
             and chemins_obtenus['restauration'] == 'sauvegardes-mw',
             f"config={sorties.get('backup_path')} obtenus={chemins_obtenus}")

# ============================================================ bilan
print("\n" + "=" * 68)
ok = sum(1 for *_, c, _ in resultats if c)
print(f" {ok}/{len(resultats)} tests reussis")
for n, nom, c, _ in resultats:
    if not c:
        print(f"   ECHEC : test {n} — {nom}")
print("=" * 68)
sys.exit(0 if ok == len(resultats) else 1)
