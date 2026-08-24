# Inventaire des sites

Une ligne par site branché au moteur. **Aucun mot de passe ici** — ils vivent
uniquement dans les secrets GitHub de chaque dépôt.

À tenir à jour au moment du branchement, pas plus tard.

| Domaine | Dépôt | Hébergeur | Protocole | Chemin distant | Statut | Version | Livré le |
|---|---|---|---|---|---|---|---|
| mwagency.ch | refonte-mw-agency | Infomaniak | sftp | `sites/mwagency.ch/` | livre | `v2` | 2026-08-24 |
| testmwagency.ch | test-auto-dist | Infomaniak | sftp | `sites/testmwagency.ch/` | livre | `v2` | — (site de test) |

## Colonnes

- **Statut** — recopié depuis `mw-config.json` du dépôt. `chantier` ou `livre`.
- **Version** — le tag du moteur que ce site utilise. Permet de savoir qui
  migrer quand une nouvelle version stable sort.
- **Livré le** — date de mise en production. Un site livré doit avoir
  `"status": "livre"` dans son `mw-config.json`.

## Contrôle avant de considérer un site comme livré

- [ ] Le déploiement passe au vert en statut `chantier`
- [ ] `mw-config.json` contient le bon domaine final
- [ ] L'audit SEO ne remonte plus de problème bloquant
- [ ] Le formulaire arrive dans la bonne boîte
- [ ] Une restauration a été testée **une fois**
- [ ] `"status": "livre"` est en place
- [ ] Un email de publication a bien été reçu
- [ ] La ligne est ajoutée à ce tableau
