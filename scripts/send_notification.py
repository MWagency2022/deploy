"""Envoi du rapport par email via les secrets MW_NOTIFY_* du depot."""
import os, smtplib, ssl, sys
from email.message import EmailMessage

hote = os.environ.get('MW_NOTIFY_HOST', '').strip()
port = int(os.environ.get('MW_NOTIFY_PORT', '587') or 587)
user = os.environ.get('MW_NOTIFY_USER', '').strip()
mdp  = os.environ.get('MW_NOTIFY_PASSWORD', '')
exp  = os.environ.get('MW_NOTIFY_FROM', '').strip() or user
dest = os.environ.get('MW_NOTIFY_TO', '').strip()

if not (hote and user and mdp and dest):
    manquants = [n for n, v in (('MW_NOTIFY_HOST', hote), ('MW_NOTIFY_USER', user),
                                ('MW_NOTIFY_PASSWORD', mdp), ('MW_NOTIFY_TO', dest)) if not v]
    print("Notification email non configuree : " + ", ".join(manquants))
    # Un email silencieusement absent est un piege : il est signale sur la page
    # du run, sans pour autant faire echouer le deploiement.
    print("::warning title=MW Agency - email non envoye::Secret(s) manquant(s) : "
          + ", ".join(manquants)
          + ". Aucun rapport de deploiement n'a ete envoye par email.")
    sys.exit(0)

dossier = sys.argv[1] if len(sys.argv) > 1 else '.'
sujet = open(os.path.join(dossier, 'mw-email-subject.txt'), encoding='utf-8').read().strip()
corps = open(os.path.join(dossier, 'mw-email-body.txt'), encoding='utf-8').read()

msg = EmailMessage()
msg['Subject'] = sujet
msg['From'] = exp
msg['To'] = dest
msg.set_content(corps)

try:
    contexte = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(hote, port, context=contexte, timeout=30) as s:
            s.login(user, mdp); s.send_message(msg)
    else:
        with smtplib.SMTP(hote, port, timeout=30) as s:
            s.ehlo(); s.starttls(context=contexte); s.ehlo()
            s.login(user, mdp); s.send_message(msg)
    print(f"Email envoye a {dest}")
    print(f"Sujet : {sujet}")
except Exception as e:
    # Un email qui ne part pas ne doit pas masquer le resultat du deploiement.
    print(f"ECHEC de l'envoi de l'email : {type(e).__name__} {e}")
    print("Le resultat du deploiement reste visible dans le resume GitHub.")
    print(f"::warning title=MW Agency - email non envoye::L'envoi du rapport a "
          f"echoue ({type(e).__name__}). Verifier les secrets MW_NOTIFY_*.")
sys.exit(0)
