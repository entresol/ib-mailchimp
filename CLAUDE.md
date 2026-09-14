# ib-mailchimp

Monatliche Neudenkertreffen-Einladung des Innovationsbeirats via Mailchimp.

Vollständiger Kontext - Backend-Zugang, Setup auf einem neuen Rechner, Workflow,
`event.yaml`-Felder, Design-Grundlage:

@~/Library/Mobile Documents/com~apple~CloudDocs/Sync/skills/i.b/mailchimp.md

@~/Library/Mobile Documents/com~apple~CloudDocs/Sync/skills/engineering-principles.md

## Schnellstart

```bash
source .venv/bin/activate
python create_campaign.py event.yaml --dry-run   # nur lokale Vorschau
python create_campaign.py event.yaml             # Entwurf + Testmail an TEST_EMAIL
```

Ohne `.env` im Projektverzeichnis läuft nichts - siehe „Einrichtung auf einem neuen Rechner"
im Skill.
