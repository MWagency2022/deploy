"""Transforme mw-report.json en resume GitHub et en corps d'email.

Deux categories de problemes, jamais melangees :
  - ce que Lovable peut corriger   -> prompt pret a copier
  - ce qui releve de l'infrastructure -> action technique decrite
"""
import json, os, sys
import mw_common as mw

sortie_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
r = mw.charger()

etat     = r.get('status_global', 'ok')
publie   = r.get('published', False)
rollback = r.get('rollback', 'none')
domaine  = r.get('domain') or '(domaine non configure)'
erreurs  = r.get('errors', [])
alertes  = r.get('warnings', [])
erreur_build = r.get('buildError')
transfert_rate = r.get('deploy') == 'failed'

lovable   = [e for e in erreurs if e.get('category', 'lovable') == 'lovable']
technique = [e for e in erreurs if e.get('category') == 'technique']

operation = r.get('operation', 'deploiement')

# ----------------------------------------------------------------- titre
if operation == 'restauration':
    sauvegarde = r.get('restoreBackup') or '(non precisee)'
    revert = r.get('revert', 'none')
    if revert == 'failed':
        titre = "ALERTE CRITIQUE - RESTAURATION ET RETOUR ARRIERE EN ECHEC"
        sujet = f"🚨 MW Agency — Restauration et retour arrière échoués — {domaine}"
    elif revert == 'done':
        titre = "RESTAURATION ANNULEE"
        sujet = f"🚨 MW Agency — Restauration annulée — {domaine}"
    elif r.get('restore') == 'failed':
        titre = "RESTAURATION INTERROMPUE"
        sujet = f"🚨 MW Agency — Restauration interrompue — {domaine}"
    elif etat == 'blocked':
        titre = "RESTAURATION BLOQUEE"
        sujet = f"❌ MW Agency — Restauration bloquée — {domaine}"
    elif r.get('restore') == 'ok' and r.get('productionCheck') == 'ok':
        titre = "RESTAURATION REUSSIE"
        sujet = f"✅ MW Agency — Restauration réussie — {domaine}"
    else:
        titre = "RESTAURATION - ETAT INDETERMINE"
        sujet = f"🚨 MW Agency — Restauration à vérifier — {domaine}"
elif rollback == 'failed':
    titre = "ALERTE CRITIQUE - RESTAURATION EN ECHEC"
    sujet = f"🚨 MW Agency — Restauration échouée, intervention requise — {domaine}"
elif rollback == 'done':
    premier = r.get('remoteState') in ('absent', 'vide')
    if premier:
        titre = "PUBLICATION ECHOUEE - ETAT INITIAL RESTAURE"
        sujet = f"🚨 MW Agency — Publication échouée, serveur remis en état — {domaine}"
    elif transfert_rate:
        titre = "TRANSFERT INTERROMPU - VERSION PRECEDENTE RESTAUREE"
        sujet = f"🚨 MW Agency — Transfert interrompu, version restaurée — {domaine}"
    else:
        titre = "NOUVELLE VERSION ANNULEE"
        sujet = f"🚨 MW Agency — Nouvelle version annulée — {domaine}"
elif rollback == 'impossible':
    titre = "ALERTE CRITIQUE" if transfert_rate else "PUBLICATION EN ECHEC"
    sujet = (f"🚨 MW Agency — {'Site potentiellement casse' if transfert_rate else 'Échec de publication'}"
             f" — {domaine}")
elif publie and etat == 'ok':
    titre, sujet = "SITE PUBLIE", f"✅ MW Agency — Site publié — {domaine}"
elif erreur_build:
    titre, sujet = "BUILD BLOQUE", f"❌ MW Agency — Build bloqué — {domaine}"
elif etat == 'blocked':
    titre, sujet = "PUBLICATION BLOQUEE", f"❌ MW Agency — Publication bloquée — {domaine}"
else:
    titre, sujet = "AUCUNE PUBLICATION", f"ℹ️ MW Agency — Aucune publication — {domaine}"

ETAPES_RESTAURATION = [("Identite du dossier", 'identity'),
                       ("Identite de la sauvegarde", 'backupIdentity'),
                       ("Filet de securite", 'safetyNet'),
                       ("Restauration", 'restore'),
                       ("Site accessible", 'productionCheck'),
                       ("Retour arriere", 'revert')]

ETAPES = [("Build", 'build'), ("Identite du dossier", 'identity'), ("SEO technique", 'seo'),
          ("Sauvegarde", 'backup'), ("Deploiement", 'deploy'), ("Site en ligne", 'productionCheck')]
if operation == 'restauration':
    ETAPES = ETAPES_RESTAURATION

LIBELLE = {'ok': 'OK', 'failed': 'ECHEC', 'not_started': 'non atteint',
           'refuse': 'REFUSEE', 'none': '-', 'done': 'effectue',
           'skipped': 'ignore', 'nouveau': 'nouveau site', 'adopte': 'adopte',
           'conflit': 'CONFLIT', 'non-marque': 'NON MARQUE',
           'erreur-connexion': 'CONNEXION IMPOSSIBLE', 'erreur-parent': 'PARENT ILLISIBLE',
           'erreur-lecture': 'LECTURE IMPOSSIBLE', 'warning': 'avertissement'}


def bloc_etapes():
    return "\n".join(f"{n} : {LIBELLE.get(r.get(k, 'not_started'), r.get(k))}"
                     for n, k in ETAPES)


def detail(p):
    l = [f"- {p['page']} — {p['message']}"]
    if p.get('found') and '\n' not in str(p['found']):
        l.append(f"   Trouve  : {p['found']}")
    if p.get('expected'):
        l.append(f"   Attendu : {p['expected']}")
    if p.get('action'):
        l.append(f"   Action  : {p['action']}")
    return "\n".join(l)


def prompt_lovable():
    if not lovable:
        return ""
    lignes = ["Corrige uniquement les problemes de publication suivants sans "
              "modifier inutilement le design ni le contenu valide :", ""]
    for i, p in enumerate(lovable, 1):
        if p['type'] == 'build':
            t = f"{i}. Le build du projet echoue. Erreur remontee :\n{p.get('found', '')}"
        else:
            t = f"{i}. [{p['page']}] {p['message']}"
            if p.get('expected'):
                t += f" Valeur attendue : {p['expected']}."
            if p.get('action'):
                t += f" {p['action']}"
        lignes.append(t)
    lignes += ["", f"Le domaine final du site est {domaine}.",
               "N'invente aucun contenu, aucune adresse, aucun avis ni aucun chiffre.",
               "Une fois corrige, ne publie pas encore le site."]
    return "\n".join(lignes)


# ------------------------------------------------------------- corps email
parties = [titre, "", domaine, ""]

if operation == 'restauration':
    sauvegarde = r.get('restoreBackup') or '(non precisee)'
    revert = r.get('revert', 'none')
    parties += [f"Sauvegarde demandee : {sauvegarde}", ""]
    if titre == "RESTAURATION REUSSIE":
        parties += [bloc_etapes()]
    elif revert == 'done':
        parties += ["La sauvegarde demandee n'etait pas fonctionnelle.", "",
                    "L'etat qui etait en ligne avant la restauration a ete remis "
                    "automatiquement.", "",
                    f"Site accessible : {'OK' if r.get('revertCheck') == 'ok' else 'A VERIFIER'}", ""]
    elif revert == 'failed':
        parties += ["La restauration et le retour arriere ont echoue.", "",
                    "Intervention technique necessaire : le site en ligne peut "
                    "etre incomplet ou indisponible.", ""]
    elif etat == 'blocked':
        parties += ["Aucun fichier n'a ete modifie.", ""]
    else:
        parties += ["Etat a verifier manuellement.", ""]
elif titre == "SITE PUBLIE":
    parties += [bloc_etapes()]
elif rollback == 'failed':
    parties += ["La restauration automatique a echoue.",
                "Une intervention technique est necessaire : le site en ligne "
                "peut etre incomplet ou indisponible.", "",
                f"Raison : {r.get('rollbackError') or 'voir le detail ci-dessous'}", ""]
elif rollback == 'done':
    etat_initial = r.get('remoteState', 'fichiers')
    cause = ("Le transfert des fichiers a echoue en cours de route."
             if transfert_rate else
             "La nouvelle version a ete transferee mais le controle de "
             "production a echoue.")
    if etat_initial == 'absent':
        parties += [cause, "",
                    "LA PUBLICATION A ECHOUE.", "",
                    "Il s'agissait du premier deploiement sur ce dossier : le "
                    "dossier cree pendant l'operation a ete supprime.",
                    "Le serveur est revenu a son etat initial.", "",
                    "Retour arriere : OK (absence du dossier verifiee)", ""]
    elif etat_initial == 'vide':
        parties += [cause, "",
                    "LA PUBLICATION A ECHOUE.", "",
                    "Il s'agissait du premier deploiement sur ce dossier : le "
                    "dossier a ete remis dans son etat vide initial.",
                    "Le serveur est revenu a son etat initial.", "",
                    "Retour arriere : OK (dossier vide verifie)", ""]
    else:
        parties += [cause, "",
                    "La version precedente a ete restauree automatiquement.", "",
                    f"Site actuel : {domaine}",
                    "Rollback : OK",
                    f"Site accessible : {'OK' if r.get('rollbackCheck') == 'ok' else 'A VERIFIER'}", ""]
elif rollback == 'impossible':
    parties += ["Le transfert des fichiers a echoue en cours de route."
                if transfert_rate else
                "Le controle de production a echoue apres le transfert.", "",
                "ROLLBACK IMPOSSIBLE : AUCUNE SAUVEGARDE VALIDE.", "",
                "Le site en ligne est peut-etre incomplet ou en anomalie. "
                "Une intervention manuelle est necessaire.", ""]
else:
    parties += ["La version actuellement en ligne n'a PAS ete modifiee.", ""]

if erreur_build:
    parties += ["=" * 60, "ERREUR DE BUILD", "=" * 60, "", erreur_build, ""]

if lovable and not erreur_build:
    parties += ["=" * 60,
                f"A CORRIGER DANS LOVABLE — {len(lovable)} point(s)",
                "=" * 60, ""]
    parties += [detail(p) + "\n" for p in lovable]

if technique:
    parties += ["=" * 60,
                f"INTERVENTION TECHNIQUE — {len(technique)} point(s)",
                "=" * 60, "",
                "Ces points ne concernent pas le site lui-meme : Lovable ne peut "
                "pas les corriger.", ""]
    parties += [detail(p) + "\n" for p in technique]

if alertes:
    parties += ["", f"{len(alertes)} avertissement(s) — non bloquant(s) :"]
    parties += [f"- {a['page']} — {a['message']}" for a in alertes]

p = prompt_lovable()
if p:
    parties += ["", "=" * 60, "PROMPT A DONNER A LOVABLE", "=" * 60, "", p]
elif technique and not lovable:
    parties += ["", "Aucun prompt Lovable : ces problemes relevent de "
                "l'infrastructure, pas du site."]

corps = "\n".join(parties).strip() + "\n"

open(os.path.join(sortie_dir, 'mw-email-subject.txt'), 'w', encoding='utf-8').write(sujet)
open(os.path.join(sortie_dir, 'mw-email-body.txt'), 'w', encoding='utf-8').write(corps)

# ------------------------------------------------------------- resume GitHub
ICONE = {"SITE PUBLIE": "✅", "PUBLICATION BLOQUEE": "❌", "BUILD BLOQUE": "❌",
         "RESTAURATION REUSSIE": "✅", "RESTAURATION BLOQUEE": "❌",
         "RESTAURATION ANNULEE": "🚨", "RESTAURATION INTERROMPUE": "🚨",
         "RESTAURATION - ETAT INDETERMINE": "🚨",
         "ALERTE CRITIQUE - RESTAURATION ET RETOUR ARRIERE EN ECHEC": "🚨",
         "NOUVELLE VERSION ANNULEE": "🚨", "PUBLICATION EN ECHEC": "🚨",
         "TRANSFERT INTERROMPU - VERSION PRECEDENTE RESTAUREE": "🚨",
         "PUBLICATION ECHOUEE - ETAT INITIAL RESTAURE": "🚨",
         "ALERTE CRITIQUE": "🚨", "ALERTE CRITIQUE - RESTAURATION EN ECHEC": "🚨",
         "AUCUNE PUBLICATION": "ℹ️"}

md = [f"# {ICONE.get(titre, '')} {titre}", "", f"**Domaine :** {domaine}  ",
      f"**Statut du site :** {r.get('status', '?')}", ""]
if titre not in ("SITE PUBLIE", "RESTAURATION REUSSIE") and rollback == 'none' \
        and r.get('revert', 'none') == 'none' and r.get('restore') != 'ok':
    md += ["> La version actuellement en ligne n'a pas ete modifiee.", ""]
md += ["| Etape | Resultat |", "|---|---|"]
md += [f"| {n} | {LIBELLE.get(r.get(k, 'not_started'), r.get(k))} |" for n, k in ETAPES]

if erreur_build:
    md += ["", "## Erreur de build", "", "```text", erreur_build, "```"]

for nom_section, liste in (("À corriger dans Lovable", lovable),
                           ("Intervention technique", technique)):
    if not liste:
        continue
    if nom_section == "À corriger dans Lovable" and erreur_build:
        continue
    md += ["", f"## {nom_section} — {len(liste)} point(s)", ""]
    for e in liste:
        md.append(f"**{e['page']} — {e['message']}**")
        if e.get('found') and '\n' not in str(e['found']):
            md.append(f"- Trouve : `{e['found']}`")
        if e.get('expected'):
            md.append(f"- Attendu : `{e['expected']}`")
        if e.get('action'):
            md.append(f"- Action : {e['action']}")
        md.append("")

if alertes:
    md += [f"## {len(alertes)} avertissement(s)", ""]
    md += [f"- **{a['page']}** — {a['message']}" for a in alertes]
if p:
    md += ["", "## Prompt a donner a Lovable", "", "```text", p, "```"]

texte_md = "\n".join(md) + "\n"
resume = os.environ.get('GITHUB_STEP_SUMMARY')
if resume:
    open(resume, 'a', encoding='utf-8').write(texte_md)
open(os.path.join(sortie_dir, 'mw-summary.md'), 'w', encoding='utf-8').write(texte_md)

print(sujet)
print()
print(corps)
