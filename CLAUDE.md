# ib-mailchimp

Monatliche Neudenkertreffen-Einladung des Innovationsbeirats via Mailchimp.

Vollständiger Kontext — Backend-Zugang, API-Key, Repo-Handling, Workflow,
`event.yaml`-Felder, Design-Grundlage:

@~/Library/Mobile Documents/com~apple~CloudDocs/Sync/skills/i.b/mailchimp.md

@~/Library/Mobile Documents/com~apple~CloudDocs/Sync/skills/engineering-principles.md

## Sofort loslegen

Diese Punkte sind entschieden — nicht neu erfragen:

- **API-Key:** steht in `.env` neben `create_campaign.py`. Direkt lesen, direkt benutzen.
  Nie ausgeben, nie committen, nicht beim User erfragen. Fehlt die `.env`, siehe
  „API-Key — Zugriff" im Skill.
- **Push:** direkt auf `main`. Kein Feature-Branch, kein PR — Solo-Repo. Ausnahme von der
  globalen Regel, gilt nur hier. `push --force` / `reset --hard` weiterhin nur mit Zustimmung.
- **Sessionstart:** `git fetch && git status -sb`. Nicht gepushte Commits sofort pushen —
  sonst klont der nächste Rechner einen veralteten Stand.
- **Testmail:** `create_campaign.py event.yaml` legt nicht nur den Entwurf an, sondern
  verschickt sofort eine Testmail an `TEST_EMAIL`. Für einen stillen Lauf: `--test-email ""`.
- **Versand an die Liste:** immer manuell in der Mailchimp-UI. Nie per API.

## Schnellstart

```bash
.venv/bin/python create_campaign.py event.yaml --dry-run   # nur lokale Vorschau
.venv/bin/python create_campaign.py event.yaml             # Entwurf + Testmail
.venv/bin/python create_campaign.py event.yaml --test-email ""   # Entwurf ohne Testmail
```

Danach in der Mailchimp-UI: Preview prüfen → Share-URL-Slug setzen → senden.
