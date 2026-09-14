#!/usr/bin/env python3
"""
Erstellt eine Mailchimp-Kampagne für das monatliche Neudenkertreffen.

Verwendung:
    python create_campaign.py event.yaml
    python create_campaign.py event.yaml --test-email you@example.com
    python create_campaign.py event.yaml --dry-run
"""

import os
import sys
import html as htmllib
import base64
import argparse
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

API_KEY              = os.environ["MAILCHIMP_API_KEY"]
DC                   = API_KEY.split("-")[-1]
BASE_URL             = f"https://{DC}.api.mailchimp.com/3.0"
LIST_ID              = os.environ["MAILCHIMP_LIST_ID"]
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
    return resp.json() if resp.content else {}

def upload_image(image_path):
    """Lädt ein lokales Bild in den Mailchimp File Manager und gibt die CDN-URL zurück."""
    path = Path(image_path)
    img_b64 = base64.b64encode(path.read_bytes()).decode()
    result = api("POST", "file-manager/files", json={
        "name": path.name,
        "file_data": img_b64,
    })
    return result["full_size_url"]

# --- HTML-Generierung --------------------------------------------------------

def h(text):
    return htmllib.escape(str(text))

DEFAULT_CLOSING = (
    "Wir freuen uns auf euch und einen guten Austausch. "
    "Wissen ist eines der wenigen Dinge, die sich vermehren, wenn man sie teilt."
)

DIVIDER = (
    '<table width="100%" border="0" cellpadding="0" cellspacing="0" '
    'style="margin-bottom: 20px;">'
    '<tr><td style="border-top: 1px solid #e8e6e3; font-size:1px; line-height:1px;">'
    "&nbsp;</td></tr></table>"
)

def render_intro_paragraphs(paragraphs):
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    parts = []
    for i, p in enumerate(paragraphs):
        margin = "0 0 18px" if i < len(paragraphs) - 1 else "0"
        parts.append(
            f'<p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; '
            f'font-size: 16px; line-height: 1.8; color: #555555; '
            f'margin: {margin}; font-weight: 300;">{h(p.strip())}</p>'
        )
    return "\n      ".join(parts)

def render_hero_event(ev):
    """Hero-Event: kompakt (eyebrow) oder erweitert (date/time/location_name/location_address)."""

    # Erweitertes Layout: Location als Hauptüberschrift, Datum/Zeit im Eyebrow
    if ev.get("location_name"):
        date  = ev.get("date", "")
        time  = ev.get("time", "")
        eyebrow_text = f"{date} · {time}" if date and time else date or time
        loc_name = h(ev["location_name"])
        loc_addr = h(ev.get("location_address", ""))
        loc_url  = ev.get("location_url", "")
        loc_inner = (
            f'<a href="{h(loc_url)}" target="_blank" '
            f'style="color: #3a3938; text-decoration: none;">{loc_name}</a>'
            if loc_url else loc_name
        )
        rows = (
            f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 14px; '
            f'font-weight: 500; color: #f2901c; margin: 0 0 6px; letter-spacing: 1px; '
            f'text-transform: uppercase;">{h(eyebrow_text)}</p>\n'
            f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 36px; '
            f'font-weight: 400; color: #3a3938; margin: 0 0 8px; letter-spacing: -0.8px; '
            f'line-height: 1.15;">{loc_inner}</p>\n'
        )
        if loc_addr:
            rows += (
                f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 13px; '
                f'color: #6b6967; margin: 0 0 10px; font-weight: 300;">{loc_addr}</p>\n'
            )
        rows += (
            f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 14px; '
            f'color: #6b6967; margin: 0; line-height: 1.75; font-weight: 300;">{h(ev["description"])}</p>\n'
        )
    else:
        # Kompaktes Eyebrow-Layout (Standard für Flowing Invitation)
        title_inner = (
            f'<a href="{h(ev["url"])}" target="_blank" '
            f'style="color: #3a3938; text-decoration: none;">{h(ev["title"])}</a>'
            if ev.get("url") else h(ev["title"])
        )
        rows = (
            f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 11px; '
            f'font-weight: 400; color: #f2901c; margin: 0 0 6px; letter-spacing: 1.5px; '
            f'text-transform: uppercase;">{h(ev.get("eyebrow", ""))}</p>\n'
            f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 36px; '
            f'font-weight: 400; color: #3a3938; margin: 0 0 8px; letter-spacing: -0.8px; '
            f'line-height: 1.15;">{title_inner}</p>\n'
            f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 14px; '
            f'color: #6b6967; margin: 0; line-height: 1.75; font-weight: 300;">{h(ev["description"])}</p>\n'
        )

    return (
        '<table width="100%" border="0" cellpadding="0" cellspacing="0" '
        'style="margin-bottom: 32px;">\n'
        "  <tr><td>\n"
        + rows +
        "  </td></tr>\n"
        "</table>"
    )

def render_compact_event(ev):
    title_inner = (
        f'<a href="{h(ev["url"])}" target="_blank" '
        f'style="color: #3a3938; text-decoration: none;">{h(ev["title"])}</a>'
        if ev.get("url") else h(ev["title"])
    )
    return (
        '<table width="100%" border="0" cellpadding="0" cellspacing="0" '
        'style="margin-bottom: 20px;">\n'
        "  <tr><td>\n"
        f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 11px; '
        f'font-weight: 400; color: #f2901c; margin: 0 0 4px; letter-spacing: 1.5px; '
        f'text-transform: uppercase;">{h(ev["eyebrow"])}</p>\n'
        f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 22px; '
        f'font-weight: 300; color: #3a3938; margin: 0 0 4px; letter-spacing: -0.5px; '
        f'line-height: 1.2;">{title_inner}</p>\n'
        f'    <p style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 13px; '
        f'color: #6b6967; margin: 0; line-height: 1.5; '
        f'font-weight: 300;">{h(ev["description"])}</p>\n'
        "  </td></tr>\n"
        "</table>"
    )

def render_cta(text, url):
    return (
        '<table width="100%" border="0" cellpadding="0" cellspacing="0" '
        'style="margin-top: 28px;">\n'
        f'  <tr><td><a href="{h(url)}" target="_blank" '
        f'style="font-family: \'Plus Jakarta Sans\', Arial, sans-serif; font-size: 15px; '
        f'font-weight: 500; color: #f2901c; text-decoration: none; '
        f'letter-spacing: 0;">{h(text)}</a></td></tr>\n'
        "</table>"
    )

def build_main_event_html(ev):
    """Hauptevent (grauer Hintergrund) + optionaler CTA."""
    parts = [render_hero_event(ev["main_event"])]
    if ev.get("cta_text") and ev.get("cta_url"):
        parts.append(render_cta(ev["cta_text"], ev["cta_url"]))
    return "\n".join(parts)

def build_extra_events_html(ev):
    """Zusätzliche Event-Kacheln (weißer Hintergrund, eigene Section)."""
    extra = ev.get("events") or []
    if not extra:
        return ""
    parts = []
    for i, event in enumerate(extra):
        if i > 0:
            parts.append(DIVIDER)
        parts.append(render_compact_event(event))
    return "\n".join(parts)

def hero_type_scale(greeting):
    """Hero-Schriftgrad nach Länge - 72px sprengt bei langen Begrüßungen die 600px.

    Liefert (Desktop-Größe, Desktop-Tracking, Mobil-Größe, Mobil-Tracking).
    """
    n = len(greeting)
    if n <= 8:
        return 72, -3, 52, -2
    if n <= 14:
        return 52, -2, 38, -1.5
    return 40, -1.5, 30, -1

def generate_html(ev, image_url=None):
    greeting         = ev.get("greeting", "Hola,")
    hero_size, hero_track, hero_size_m, hero_track_m = hero_type_scale(greeting)
    subtitle         = ev.get("subtitle", "")
    intro            = ev.get("intro", [])
    closing          = ev.get("closing") or DEFAULT_CLOSING
    team             = ev.get("team", "Das Neudenkertreffen-Team")
    main_event_html  = build_main_event_html(ev)
    extra_events_html = build_extra_events_html(ev)

    image_section = ""
    if image_url:
        image_section = f"""
  <!-- IMAGE -->
  <tr>
    <td bgcolor="#ffffff" style="padding: 0; line-height: 0; font-size: 0;">
      <img src="{h(image_url)}" width="600" alt="" style="display:block; width:100%; max-width:600px; height:auto;">
    </td>
  </tr>"""

    extra_section = ""
    if extra_events_html:
        extra_section = f"""
  <!-- EXTRA EVENTS -->
  <tr>
    <td bgcolor="#ffffff" style="padding: 72px 40px 0;" class="pad">
{extra_events_html}
    </td>
  </tr>"""

    return f"""\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>*|MC:SUBJECT|*</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200;0,300;0,400;0,600;0,700;1,300;1,400&display=swap" rel="stylesheet" type="text/css">
  <style type="text/css">
    body, #bodyTable {{ margin: 0; padding: 0; width: 100%; background-color: #f0eeeb; font-family: 'Plus Jakarta Sans', Arial, sans-serif; }}
    p, a, span, td {{ font-family: 'Plus Jakarta Sans', Arial, sans-serif; }}
    img {{ border: 0; height: auto; outline: none; text-decoration: none; }}
    table {{ border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
    a {{ -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; }}
    @media only screen and (max-width: 620px) {{
      .email-container {{ width: 100% !important; }}
      .hero-text {{ font-size: {hero_size_m}px !important; letter-spacing: {hero_track_m}px !important; }}
      .hero-sub {{ font-size: 22px !important; }}
      .pad {{ padding: 36px 28px !important; }}
    }}
  </style>
</head>
<body bgcolor="#f0eeeb">
<table border="0" cellpadding="0" cellspacing="0" width="100%" id="bodyTable">
<tr>
<td align="center" valign="top" style="padding: 28px 0 48px;">

<table border="0" cellpadding="0" cellspacing="0" width="600" class="email-container" style="max-width:600px; background-color:#ffffff; border-radius: 6px;">

  <!-- TOP BAR -->
  <tr>
    <td style="padding: 24px 40px 0;" class="pad" bgcolor="#ffffff">
      <table width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
          <td valign="middle">
            <a href="https://innovationsbeirat.de/" target="_blank" style="text-decoration: none;"><span style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 21px; font-weight: 600; color: #f2901c; letter-spacing: 0;">neu.</span><span style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 21px; font-weight: 400; color: #3a3938; letter-spacing: 0;">denken</span></a>
          </td>
          <td align="right" valign="middle">
            <a href="*|ARCHIVE|*" style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 10px; color: #bbbbbb; text-decoration: none; letter-spacing: 0.5px;">Im Browser ansehen</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- HERO -->
  <tr>
    <td bgcolor="#ffffff" style="padding: 40px 40px 0;" class="pad">
      <p class="hero-text" style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: {hero_size}px; font-weight: 200; color: #3a3938; margin: 0; letter-spacing: {hero_track}px; line-height: 1.0;">{h(greeting)}</p>
      <p class="hero-sub" style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 18px; font-weight: 300; font-style: italic; color: #f2901c; margin: 16px 0 0; letter-spacing: 0; line-height: 1.3;">{h(subtitle)}</p>
    </td>
  </tr>

  <!-- INTRO -->
  <tr>
    <td bgcolor="#ffffff" style="padding: 48px 40px 40px;" class="pad">
      {render_intro_paragraphs(intro)}
    </td>
  </tr>

  <!-- MAIN EVENT -->
  <tr>
    <td bgcolor="#f7f6f4" style="padding: 36px 40px 40px;" class="pad">
{main_event_html}
    </td>
  </tr>
{image_section}
{extra_section}
  <!-- CLOSING -->
  <tr>
    <td bgcolor="#ffffff" style="padding: 40px 40px 0;" class="pad">
      <table width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr><td style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 16px; line-height: 1.8; color: #555555; font-weight: 300; padding-bottom: 28px;">{h(closing)}</td></tr>
        <tr><td style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 16px; line-height: 1.8; color: #555555; font-weight: 300; padding-bottom: 2px;">Herzliche Grüße</td></tr>
        <tr><td style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 16px; line-height: 1.8; color: #555555; font-weight: 300; padding-bottom: 44px;">{h(team)}</td></tr>
      </table>
    </td>
  </tr>

  <!-- FOOTER RULE -->
  <tr>
    <td bgcolor="#f2901c" style="height: 1px; font-size: 1px; line-height: 1px;">&nbsp;</td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td bgcolor="#e6e6e7" style="padding: 28px 40px 32px; border-radius: 0 0 6px 6px;">
      <p style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 12px; font-weight: 400; color: #5a5b5d; margin: 0 0 12px; line-height: 2.2;">
        <a href="https://innovationsbeirat.de/open-first/" target="_blank" style="color: #f2901c; text-decoration: none;">Open First</a>
        &nbsp;&nbsp;·&nbsp;&nbsp;
        <a href="https://betreute-intelligenz.ai/" target="_blank" style="color: #f2901c; text-decoration: none;">Betreute Intelligenz</a>
        &nbsp;&nbsp;·&nbsp;&nbsp;
        <a href="https://innovationsbeirat.de/innovation-lunch/" target="_blank" style="color: #f2901c; text-decoration: none;">Innovation Lunch</a>
        &nbsp;&nbsp;<span style="color: #b0b0b2;">|</span>&nbsp;&nbsp;
        <a href="https://signal.group/#CjQKIB0u9sAxHA27EUoBWPLKD50rdCB2VYANroB-K-jbCHHyEhDUe9IUru6nYJD-I4oZYAvL" target="_blank" style="color: #f2901c; text-decoration: none;">Signal</a>
        &nbsp;&nbsp;·&nbsp;&nbsp;
        <a href="https://chat.innovationsbeirat.de/" target="_blank" style="color: #f2901c; text-decoration: none;">Mattermost</a>
        &nbsp;&nbsp;·&nbsp;&nbsp;
        <a href="https://nuernberg.social/" target="_blank" style="color: #f2901c; text-decoration: none;">Mastodon</a>
      </p>
      <p style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 11px; font-weight: 300; color: #9a9a9c; margin: 16px 0 0; line-height: 2;">
        &copy; *|CURRENT_YEAR|* Innovationsbeirat &nbsp;&middot;&nbsp;
        <a href="mailto:open@innovationsbeirat.de" style="color: #9a9a9c; text-decoration: none;">open@innovationsbeirat.de</a>
        &nbsp;&middot;&nbsp;
        <a href="*|UPDATE_PROFILE|*" style="color: #9a9a9c; text-decoration: none;">Einstellungen</a>
        &nbsp;&middot;&nbsp;
        <a href="*|UNSUB|*" style="color: #9a9a9c; text-decoration: none;">Austragen</a>
      </p>
    </td>
  </tr>

</table>
</td>
</tr>
</table>
</body>
</html>"""

# --- Kampagne erstellen ------------------------------------------------------

def create_campaign(ev, dry_run=False):
    yaml_dir = Path(ev.get("_yaml_dir", "."))
    image_url = None

    if ev.get("image"):
        image_path = yaml_dir / ev["image"]
        if dry_run:
            # Relative Pfad für lokale Browser-Vorschau
            image_url = str(image_path)
        else:
            print(f"Lade Bild hoch: {image_path.name}...")
            image_url = upload_image(image_path)
            print(f"Bild-URL: {image_url}")

    generated_html = generate_html(ev, image_url=image_url)

    print(f"\nBetreff:  {ev['betreff']}")
    print(f"Greeting: {ev.get('greeting', '—')}")
    print(f"Typ:      {ev.get('typ', '—')}")

    if dry_run:
        preview_path = Path(__file__).parent / "preview_draft.html"
        preview_path.write_text(generated_html, encoding="utf-8")
        print(f"\n[Dry-run] Vorschau gespeichert: {preview_path}")
        return None

    print("\nDupliziere Vorlage...")
    new = api("POST", f"campaigns/{TEMPLATE_CAMPAIGN_ID}/actions/replicate")
    campaign_id = new["id"]
    print(f"Neue Kampagne: {campaign_id}")

    print("Aktualisiere Einstellungen...")
    api("PATCH", f"campaigns/{campaign_id}", json={
        "settings": {
            "title": ev["betreff"],
            "subject_line": ev["betreff"],
            "preview_text": ev.get("vorschautext", ""),
            "from_name": "Stefan Probst",
            "reply_to": "open@innovationsbeirat.de",
        }
    })

    print("Lade HTML hoch...")
    api("PUT", f"campaigns/{campaign_id}/content", json={"html": generated_html})

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
    parser.add_argument("--dry-run", action="store_true", help="Vorschau lokal speichern, nichts bei Mailchimp anlegen")
    args = parser.parse_args()

    event_path = Path(args.event)
    if not event_path.exists():
        print(f"Datei nicht gefunden: {event_path}")
        sys.exit(1)

    ev = yaml.safe_load(event_path.read_text(encoding="utf-8"))
    ev["_yaml_dir"] = str(event_path.parent.resolve())
    campaign_id = create_campaign(ev, dry_run=args.dry_run)

    if campaign_id and args.test_email:
        send_test(campaign_id, args.test_email)
    elif campaign_id:
        print("\nKein Test-Empfänger angegeben. Testmail übersprungen.")

    if campaign_id:
        print(f"\nCampaign ID: {campaign_id}")
        print("Jetzt in Mailchimp prüfen (Preview) und manuell versenden.")

if __name__ == "__main__":
    main()
