#!/usr/bin/env python3
"""
Erstellt eine Mailchimp-Kampagne für das monatliche Neudenkertreffen.

Verwendung:
    python create_campaign.py event.yaml [--test-email you@example.com]
    python create_campaign.py event.yaml --dry-run
"""

import os
import re
import sys
import json
import argparse
import textwrap
from pathlib import Path

try:
    import yaml
    import requests
except ImportError:
    print("Fehlende Pakete. Installieren mit: pip install pyyaml requests")
    sys.exit(1)

# --- Konfiguration -----------------------------------------------------------

def load_config():
    env = Path(__file__).parent / ".env"
    cfg = {}
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    for k, v in cfg.items():
        os.environ.setdefault(k, v)

load_config()

API_KEY  = os.environ["MAILCHIMP_API_KEY"]
DC       = API_KEY.split("-")[-1]
BASE_URL = f"https://{DC}.api.mailchimp.com/3.0"
LIST_ID  = os.environ["MAILCHIMP_LIST_ID"]
TEMPLATE_CAMPAIGN_ID = os.environ["MAILCHIMP_TEMPLATE_CAMPAIGN_ID"]
DEFAULT_TEST_EMAIL   = os.environ.get("TEST_EMAIL", "")

# --- Mailchimp API -----------------------------------------------------------

def api(method, path, **kwargs):
    resp = requests.request(
        method,
        f"{BASE_URL}/{path}",
        auth=("anystring", API_KEY),
        **kwargs,
    )
    if not resp.ok:
        print(f"API-Fehler {resp.status_code}: {resp.text}")
        sys.exit(1)
    if resp.content:
        return resp.json()
    return {}

# --- HTML-Inhalte ersetzen ---------------------------------------------------

def build_address_html(lines, url):
    """Baut den Adressblock als HTML (Zeilenumbrüche + Link)."""
    parts = [f'<span style="font-size:15px"><span style="font-family:open sans,helvetica neue,helvetica,arial,sans-serif">']
    parts.append("<br>\n".join(line.strip() for line in lines if line.strip()))
    parts.append('</span></span><br>\n')
    parts.append(
        f'<a href="{url}" target="_blank" style="mso-line-height-rule: exactly;'
        f'-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%;'
        f'color: #f2901c;font-weight: normal;text-decoration: none;">'
        f'<span style="font-size:15px"><span style="font-family:open sans,helvetica neue,'
        f'helvetica,arial,sans-serif">{url}</span></span></a>'
    )
    return "".join(parts)

def build_body_html(text):
    """Wandelt Fließtext (mit Leerzeilen als Absätze) in HTML-Zeilenumbrüche um."""
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "<br>\n<br>\n".join(
        p.replace("\n", "<br>\n") for p in paragraphs
    )

def update_html(html, event):
    """Ersetzt die variablen Inhalte in der Kampagnen-HTML."""

    # 1. Einleitungstext nach "Kia ora,"
    intro_html = build_body_html(event["intro"])
    html = re.sub(
        r"(Kia ora,<br>\n<br>\n)(.+?)(</span></span></p>)",
        lambda m: m.group(1) + intro_html + m.group(3),
        html,
        flags=re.DOTALL,
    )

    # 2. Datumszeile
    html = re.sub(
        r"(am [^<]+? von [^<]+? Uhr im)",
        event["datum_zeile"],
        html,
    )

    # 3. Ortsname (fett, grau)
    html = re.sub(
        r"(<font color=\"#696969\"[^>]*><span[^>]*><strong>)(.+?)(</strong>)",
        lambda m: m.group(1) + event["ort_name"] + m.group(3),
        html,
    )

    # 4. Adressblock + URL (Anker: nach dem Ortsnamen-Font-Tag)
    address_lines = [l for l in event["adresse"].splitlines() if l.strip()]
    new_addr = build_address_html(address_lines, event["ort_url"])
    html = re.sub(
        r'(</font><br>\n<br>\n)'
        r'<span style="font-size:15px"><span style="font-family:open sans[^"]*">'
        r'.+?</span></span><br>\n<a href="[^"]*"[^>]*>.+?</a>',
        lambda m: m.group(1) + new_addr,
        html,
        count=1,
        flags=re.DOTALL,
    )

    # 5. Wegbeschreibung + Programm
    body_html = build_body_html(event["wegweiser_und_programm"])
    html = re.sub(
        r"(Du findest .+?)(<br>\n<br>\nMelde dich)",
        lambda m: body_html + m.group(2),
        html,
        flags=re.DOTALL,
    )

    return html

def update_plain(plain, event):
    """Ersetzt die variablen Inhalte im Plaintext."""

    def clean(text):
        return textwrap.fill(text.strip().replace("\n", " "), width=9999).strip()

    # 1. Intro
    plain = re.sub(
        r"(Kia ora,\n\n)(.+?)(\n\n\n?\*\*)",
        lambda m: m.group(1) + clean(event["intro"]) + "\n\n\n" + m.group(3).lstrip("\n"),
        plain,
        flags=re.DOTALL,
    )

    # 2. Datumszeile
    plain = re.sub(
        r"am .+? von .+? Uhr im",
        event["datum_zeile"],
        plain,
    )

    # 3. Ortsname
    address_lines = [l for l in event["adresse"].splitlines() if l.strip()]
    old_location_block_pattern = (
        r"([A-Za-zÄÖÜäöüß ]+\n\n"  # Ortsname
        r"[^\n]+\n[^\n]+\n[^\n]+\n"  # Adresse (3 Zeilen)
        r"https?://[^\n]+\n)"        # URL
    )
    new_location_block = (
        event["ort_name"] + "\n\n"
        + "\n".join(address_lines) + "\n"
        + event["ort_url"] + "\n"
    )
    plain = re.sub(old_location_block_pattern, new_location_block, plain, count=1)

    # 4. Wegbeschreibung + Programm
    body_text = "\n\n".join(
        p.strip().replace("\n", " ")
        for p in event["wegweiser_und_programm"].strip().split("\n\n")
        if p.strip()
    )
    plain = re.sub(
        r"(Du findest .+?)(Melde dich)",
        lambda m: body_text + "\n\n" + m.group(2),
        plain,
        flags=re.DOTALL,
    )

    return plain

# --- Kampagne erstellen ------------------------------------------------------

def create_campaign(event, dry_run=False):
    print(f"\nVorlage: Kampagne {TEMPLATE_CAMPAIGN_ID}")
    print(f"Typ:     {event['typ']}")
    print(f"Betreff: {event['betreff']}")

    if dry_run:
        print("\n[Dry-run] Kampagne wird nicht angelegt.")
        return None

    # Letzte Kampagne duplizieren
    print("\nDupliziere Vorlage...")
    new = api("POST", f"campaigns/{TEMPLATE_CAMPAIGN_ID}/actions/replicate")
    campaign_id = new["id"]
    print(f"Neue Kampagne: {campaign_id}")

    # Einstellungen aktualisieren
    print("Aktualisiere Einstellungen...")
    api("PATCH", f"campaigns/{campaign_id}", json={
        "settings": {
            "subject_line": event["betreff"],
            "preview_text": event.get("vorschautext", ""),
            "from_name": "Stefan Probst",
            "reply_to": "open@innovationsbeirat.de",
        }
    })

    # Inhalt laden, anpassen, hochladen
    print("Lade Inhalt...")
    content = api("GET", f"campaigns/{campaign_id}/content")
    new_html  = update_html(content["html"], event)
    new_plain = update_plain(content["plain_text"], event)

    print("Lade aktualisierten Inhalt hoch...")
    api("PUT", f"campaigns/{campaign_id}/content", json={
        "html": new_html,
        "plain_text": new_plain,
    })

    return campaign_id

def send_test(campaign_id, test_email):
    print(f"\nSende Testmail an {test_email}...")
    api("POST", f"campaigns/{campaign_id}/actions/test", json={
        "test_emails": [test_email],
        "send_type": "html",
    })
    print("Testmail gesendet.")

# --- Hauptprogramm -----------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Neudenkertreffen-Einladung erstellen")
    parser.add_argument("event", help="YAML-Datei mit Veranstaltungsdaten")
    parser.add_argument("--test-email", default=DEFAULT_TEST_EMAIL, help="Empfänger der Testmail")
    parser.add_argument("--dry-run", action="store_true", help="Nur Vorschau, nichts anlegen")
    args = parser.parse_args()

    event_path = Path(args.event)
    if not event_path.exists():
        print(f"Datei nicht gefunden: {event_path}")
        sys.exit(1)

    event = yaml.safe_load(event_path.read_text())
    campaign_id = create_campaign(event, dry_run=args.dry_run)

    if campaign_id and args.test_email:
        send_test(campaign_id, args.test_email)
        mailchimp_url = f"https://us{DC.replace('us','')}.admin.mailchimp.com/campaigns/show?id={campaign_id}"
        print(f"\nKampagne in Mailchimp: https://mc.us19.mailchimp.com/campaigns")
    elif campaign_id:
        print("\nKein Test-Empfänger angegeben. Testmail übersprungen.")
        print("Kampagne wurde angelegt – bitte in Mailchimp prüfen.")

    if campaign_id:
        print(f"\nCampaign ID: {campaign_id}")
        print("Jetzt in Mailchimp öffnen und manuell versenden.")

if __name__ == "__main__":
    main()
