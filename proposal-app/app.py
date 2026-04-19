"""
Proposal & Contract Generator
Triggered by Fireflies webhook → fetches transcript → GPT-4.1 generates
offer email + consulting contract → creates two Google Docs.
"""

import os
import json
import hmac
import hashlib
import pickle
import logging
import requests
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, redirect, session
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

# ─── Bootstrap ────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR.parent / '.env')   # dev  (local repo)
load_dotenv(dotenv_path=BASE_DIR / '.env')           # prod (server)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('PROPOSALS_SECRET_KEY', 'proposals-secret-2026-change-me')

# ─── Configuration ────────────────────────────────────────────────────────────

FIREFLIES_API_KEY        = os.environ.get('Fireflies_API_Key', '')
FIREFLIES_WEBHOOK_SECRET = os.environ.get('FIREFLIES_WEBHOOK_SECRET', '')
FIREFLIES_GQL            = 'https://api.fireflies.ai/graphql'

AZURE_KEY        = os.environ.get('AZURE_OPENAI_API_KEY', '')
AZURE_ENDPOINT   = os.environ.get('AZURE_OPENAI_ENDPOINT', '').rstrip('/')
AZURE_DEPLOYMENT = 'gpt-4.1'
AZURE_API_VER    = os.environ.get('AZURE_OPENAI_API_VERSION', '2025-01-01-preview')

APP_BASE_URL  = 'https://45-32-237-144.sslip.io'
LOGO_URL      = f'{APP_BASE_URL}/static/logo.png'
REDIRECT_URI  = f'{APP_BASE_URL}/oauth/callback'

TOKEN_PATH          = BASE_DIR / 'google_token.pickle'
CLIENT_SECRET_FILE  = next(
    (p for p in [
        BASE_DIR / 'client_secret.json',
        *sorted((BASE_DIR.parent).glob('client_secret_*.json')),
    ] if p.exists()),
    None,
)

GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
]

# ─── Templates (embedded in code so the LLM can reference them) ───────────────

CONTRACT_EXAMPLE = """\
Consulting Agreement

This Consulting Agreement ("Agreement") is made between:

Client
[Company_Name]
[Company_Street]
[Zip, City, Country]
("Client")

Contractor
Limitless AI Solutions LLC
1309 Coffeen Avenue STE 1200
Sheridan, WY 82801, USA
("Contractor")

Effective Date: [TODAY]

1. Scope of Work
Contractor provides AI automation and software development services for Client.
The initial focus areas include:
• [deliverable 1 from transcript]
• [deliverable 2 from transcript]
Further tasks may be defined jointly on an ongoing basis. The scope may evolve
monthly as agreed between Client and Contractor.

2. Compensation
• Hourly rate: USD $[rate] per hour
• Billing cycle: Monthly, based on actual hours worked
• Payment terms: Net 14 days from invoice date
• Invoices: Issued by Contractor's US LLC. Payments made via international
  transfer to Contractor's designated account.
Contractor will provide a transparent report of hours worked and tasks completed.

3. Client Responsibilities
Client agrees to:
• Provide necessary system access, API keys, and credentials.
• Provide accounts for server hosting and API usage.
• Communicate priorities and approximate monthly budget expectations.

4. Ownership and Intellectual Property
Upon full payment, all deliverables and code created under this Agreement become
the property of Client. Contractor retains the right to reuse general knowledge,
non-confidential code snippets, and frameworks developed.

5. Confidentiality
Both parties agree to maintain confidentiality of business information, data,
and access credentials.

6. Termination
This Agreement is valid until terminated by either party with written notice.
Client shall compensate Contractor for all hours worked up to the termination date.
If no termination notice is given, the collaboration continues on a month-to-month basis.

7. Governing Law
This Agreement is governed by the laws of Wyoming, USA.

Signatures
[Client_name]
[Company_name]
Date: _____________

Dominik Felber
Limitless AI Solutions LLC
Date: [TODAY]\
"""

EMAIL_EXAMPLE_DE = """\
Hi [Kunden_Vorname],

Vielen Dank für das produktive Gespräch heute.

Ich habe mir nach unserem Call ausführlich Gedanken gemacht und möchte dir hiermit mein Angebot vorstellen.

[Eigentliches_Angebot]
(Mischung aus Bullet Points und kurzen leicht verständlichen Sätzen, was genau gemacht werden soll und was es kosten wird)

Lass mich wissen, ob das für dich passt, dann können wir direkt beginnen. Ich werde dann einen einfachen Vertrag aufsetzen, der unsere Zusammenarbeit offiziell festhält.

Ich lasse dir separat noch eine Übersicht zukommen, was genau ich an Inputs deinerseits benötige, um mit meiner Arbeit starten zu können.

Ich freue mich auf die Zusammenarbeit mit dir!

Viele Grüße
Dominik\
"""

EMAIL_EXAMPLE_EN = """\
Hi [Client_First_Name],

Thank you very much for the productive conversation today.

After our call, I took some time to think everything through in detail, and I would like to present my proposal to you here.

[Actual_Offer]
(A mix of bullet points and short, easy-to-understand sentences describing exactly what will be done and what it will cost)

Let me know if this works for you, and we can get started right away. I will then prepare a simple contract to officially document our collaboration.

I will also send you a separate overview outlining exactly what inputs I will need from your side in order to begin my work.

I'm looking forward to working with you!

Best regards,
Dominik\
"""

SYSTEM_PROMPT = f"""You are an assistant for Dominik Felber at Limitless AI Solutions LLC \
(AI automation consulting). Your job is to analyze a sales/discovery call transcript and \
generate a proposal email + a consulting contract.

=== STRICT RULES ===
1. Detect whether the meeting was conducted in German or English. \
   Write BOTH documents in that same language.
2. Stick STRICTLY to what was actually discussed. Do NOT invent tasks, features, \
   or pricing that were not explicitly mentioned.
3. If hourly rate is not discussed, default to USD $120/hr.
4. The email must closely follow the template below — only fill in the offer section.
5. The contract must follow the exact structure of the template below.
6. Extract the client's first name, last name, company, and address from the transcript.

=== CONTRACTOR (use verbatim, always) ===
Limitless AI Solutions LLC
1309 Coffeen Avenue STE 1200
Sheridan, WY 82801, USA
Contact person: Dominik Felber

=== EMAIL TEMPLATE (German) ===
{EMAIL_EXAMPLE_DE}

=== EMAIL TEMPLATE (English) ===
{EMAIL_EXAMPLE_EN}

=== CONTRACT TEMPLATE ===
{CONTRACT_EXAMPLE}

=== OUTPUT FORMAT ===
Respond ONLY with a JSON object (no markdown fences) with these exact keys:
{{
  "language": "de" or "en",
  "client_first_name": "...",
  "client_last_name": "...",
  "client_company": "...",
  "client_street": "...",
  "client_city_zip_country": "...",
  "email_subject": "...",
  "email_body": "complete ready-to-send email, \\n for newlines",
  "contract_body": "complete contract all sections filled, \\n for newlines"
}}

Replace ALL [placeholders] in the contract. [TODAY] = today's date."""


# ─── Fireflies helpers ────────────────────────────────────────────────────────

def _gql(query: str, variables: dict = None) -> dict:
    r = requests.post(
        FIREFLIES_GQL,
        json={'query': query, 'variables': variables or {}},
        headers={
            'Authorization': f'Bearer {FIREFLIES_API_KEY}',
            'Content-Type': 'application/json',
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if 'errors' in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data.get('data', {})


TRANSCRIPT_QUERY = """
query Transcript($id: String!) {
  transcript(id: $id) {
    id
    title
    date
    duration
    host_email
    organizer_email
    participants
    summary {
      keywords
      action_items
      outline
      overview
      bullet_gist
      short_summary
    }
    sentences {
      index
      speaker_name
      text
      start_time
      end_time
    }
  }
}
"""

TRANSCRIPTS_LIST_QUERY = """
query Transcripts($limit: Int) {
  transcripts(limit: $limit) {
    id
    title
    date
    organizer_email
    participants
    summary {
      overview
    }
  }
}
"""


def fetch_transcript(tid: str) -> dict:
    data = _gql(TRANSCRIPT_QUERY, {'id': tid})
    t = data.get('transcript')
    if not t:
        raise ValueError(f'No transcript found for id={tid}')
    return t


def fetch_recent_transcripts(limit: int = 10) -> list:
    data = _gql(TRANSCRIPTS_LIST_QUERY, {'limit': limit})
    return data.get('transcripts', [])


def verify_signature(payload: bytes, sig_header: str) -> bool:
    if not FIREFLIES_WEBHOOK_SECRET:
        log.warning('FIREFLIES_WEBHOOK_SECRET not set — skipping signature check')
        return True
    expected = 'sha256=' + hmac.new(
        FIREFLIES_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig_header or '')


# ─── Azure OpenAI ─────────────────────────────────────────────────────────────

def generate_documents(transcript: dict) -> dict:
    """Call GPT-4.1 to generate offer email and contract from transcript."""
    sentences  = transcript.get('sentences') or []
    full_text  = '\n'.join(
        f"{s['speaker_name']}: {s['text']}"
        for s in sentences if s.get('text')
    )[:9000]

    summary = transcript.get('summary') or {}

    user_msg = f"""Meeting title: {transcript.get('title', '')}
Date: {transcript.get('date', '')}
Participants: {', '.join(transcript.get('participants') or [])}
Organizer: {transcript.get('organizer_email', '')}

Summary:
{summary.get('overview', '')}

Action items:
{summary.get('action_items', '')}

Key bullet points:
{summary.get('bullet_gist', '')}

Full transcript:
{full_text}"""

    url = (
        f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}"
        f"/chat/completions?api-version={AZURE_API_VER}"
    )
    r = requests.post(
        url,
        headers={'api-key': AZURE_KEY, 'Content-Type': 'application/json'},
        json={
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user',   'content': user_msg},
            ],
            'temperature': 0.2,
            'max_tokens':  4096,
            'response_format': {'type': 'json_object'},
        },
        timeout=90,
    )
    r.raise_for_status()
    raw = r.json()['choices'][0]['message']['content']
    return json.loads(raw)


# ─── Google OAuth ─────────────────────────────────────────────────────────────

def get_creds() -> Credentials | None:
    if not TOKEN_PATH.exists():
        return None
    with open(TOKEN_PATH, 'rb') as f:
        creds = pickle.load(f)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
            _save_creds(creds)
            return creds
        except Exception as e:
            log.error('Token refresh failed: %s', e)
    return None


def _save_creds(creds: Credentials) -> None:
    with open(TOKEN_PATH, 'wb') as f:
        pickle.dump(creds, f)


# ─── HTML builders ────────────────────────────────────────────────────────────

def _lines_to_html(text: str, is_contract: bool = False) -> str:
    """Convert plain-text document to HTML suitable for Google Drive import."""
    lines  = text.split('\n')
    parts  = []
    in_ul  = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            parts.append('</ul>')
            in_ul = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            close_ul()
            parts.append('<p>&nbsp;</p>')
            continue

        # Bullet points
        if stripped.startswith(('• ', '- ', '– ')):
            item = stripped[2:].strip()
            if not in_ul:
                parts.append('<ul>')
                in_ul = True
            parts.append(f'<li>{item}</li>')
            continue

        close_ul()

        # Contract-specific heading detection
        if is_contract:
            if stripped == 'Consulting Agreement':
                # Title row handled separately in outer wrapper
                continue
            if (stripped[0].isdigit() and '. ' in stripped[:4]) or stripped == 'Signatures':
                parts.append(
                    f'<h2 style="font-family:Arial,sans-serif;font-size:14pt;'
                    f'font-weight:bold;margin-top:18pt;">{stripped}</h2>'
                )
                continue
            # Bold labels: Client, Contractor, Effective Date, ("Client"), ("Contractor")
            if stripped in ('Client', 'Contractor') or stripped.startswith('Effective Date:') \
                    or stripped.startswith('("'):
                parts.append(f'<p><strong>{stripped}</strong></p>')
                continue

        # Date line in contract signatures
        if stripped.startswith('Date:'):
            parts.append(f'<p>{stripped}</p>')
            continue

        parts.append(f'<p style="margin:4pt 0;line-height:1.5;">{stripped}</p>')

    close_ul()
    return '\n'.join(parts)


def build_contract_html(data: dict) -> str:
    body_html = _lines_to_html(data.get('contract_body', ''), is_contract=True)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body  {{ font-family: Arial, sans-serif; font-size: 11pt; margin: 40px; color: #1a1a1a; }}
  h1   {{ font-size: 26pt; font-weight: bold; margin: 0; }}
  h2   {{ font-size: 13pt; font-weight: bold; margin-top: 18pt; }}
  p    {{ margin: 5pt 0; line-height: 1.55; }}
  ul   {{ margin: 4pt 0 4pt 20pt; }}
  li   {{ margin: 2pt 0; line-height: 1.5; }}
  .logo-row {{ display: table; width: 100%; margin-bottom: 24pt; }}
  .title-cell {{ display: table-cell; vertical-align: middle; }}
  .logo-cell  {{ display: table-cell; vertical-align: middle;
                 text-align: right; width: 200px; }}
</style>
</head>
<body>
<div class="logo-row">
  <div class="title-cell"><h1>Consulting Agreement</h1></div>
  <div class="logo-cell">
    <img src="{LOGO_URL}" width="180" alt="Limitless AI Solutions">
  </div>
</div>
{body_html}
</body>
</html>"""


def build_offer_html(data: dict) -> str:
    body_html = _lines_to_html(data.get('email_body', ''))
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 11pt; margin: 40px; color: #1a1a1a; }}
  p    {{ margin: 5pt 0; line-height: 1.55; }}
  ul   {{ margin: 4pt 0 4pt 20pt; }}
  li   {{ margin: 2pt 0; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


# ─── Google Docs creation ─────────────────────────────────────────────────────

def create_google_docs(data: dict) -> dict:
    creds = get_creds()
    if not creds:
        return {'error': 'not_authenticated'}

    drive = build('drive', 'v3', credentials=creds)
    today = datetime.now().strftime('%B %d, %Y')
    company = data.get('client_company') or 'Client'

    # ── Offer email doc ────────────────────────────────────────────────────
    offer_html = build_offer_html(data)
    offer_file = drive.files().create(
        body={
            'name': f"Proposal – {company} – {today}",
            'mimeType': 'application/vnd.google-apps.document',
        },
        media_body=MediaInMemoryUpload(
            offer_html.encode('utf-8'), mimetype='text/html',
        ),
        fields='id',
    ).execute()
    offer_id  = offer_file['id']
    offer_url = f'https://docs.google.com/document/d/{offer_id}/edit'

    # ── Contract doc ───────────────────────────────────────────────────────
    contract_html = build_contract_html(data)
    contract_file = drive.files().create(
        body={
            'name': f"Contract – {company} – {today}",
            'mimeType': 'application/vnd.google-apps.document',
        },
        media_body=MediaInMemoryUpload(
            contract_html.encode('utf-8'), mimetype='text/html',
        ),
        fields='id',
    ).execute()
    contract_id  = contract_file['id']
    contract_url = f'https://docs.google.com/document/d/{contract_id}/edit'

    return {
        'offer_doc_id':   offer_id,
        'offer_url':      offer_url,
        'contract_doc_id': contract_id,
        'contract_url':   contract_url,
    }


# ─── Core pipeline ────────────────────────────────────────────────────────────

def process_meeting(meeting_id: str) -> dict:
    log.info('▸ Fetching transcript %s', meeting_id)
    transcript = fetch_transcript(meeting_id)

    log.info('▸ Generating documents via GPT-4.1')
    doc_data = generate_documents(transcript)
    log.info('  language=%s  client=%s %s',
             doc_data.get('language'), doc_data.get('client_first_name'),
             doc_data.get('client_last_name'))

    log.info('▸ Creating Google Docs')
    docs_result = create_google_docs(doc_data)

    return {
        'meeting_id': meeting_id,
        'title':      transcript.get('title', ''),
        'date':       transcript.get('date', ''),
        'doc_data':   doc_data,
        'docs':       docs_result,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

# ── Fireflies webhook ──────────────────────────────────────────────────────────

@app.route('/webhook/fireflies', methods=['POST'])
def webhook():
    payload = request.get_data()
    sig     = request.headers.get('X-Hub-Signature', '')

    if not verify_signature(payload, sig):
        log.warning('Rejected webhook — bad signature')
        return jsonify({'error': 'invalid signature'}), 401

    body = request.get_json(force=True, silent=True) or {}
    log.info('Webhook received: %s', body)

    # Supports both Webhooks V1 ("Transcription completed" / meetingId)
    # and Webhooks V2 ("meeting.transcribed" / meeting_id)
    event      = body.get('event') or body.get('eventType', '')
    meeting_id = body.get('meeting_id') or body.get('meetingId', '')

    accepted = {'meeting.transcribed', 'meeting.summarized', 'Transcription completed'}
    if event not in accepted or not meeting_id:
        return jsonify({'status': 'ignored', 'event': event}), 200

    try:
        result = process_meeting(meeting_id)
        log.info('Done. Docs: %s', result.get('docs'))
        return jsonify({'status': 'ok', 'docs': result['docs']}), 200
    except Exception as e:
        log.error('Pipeline failed: %s', e, exc_info=True)
        return jsonify({'error': str(e)}), 500


# ── Manual trigger (curl-friendly, for testing) ────────────────────────────────

@app.route('/trigger', methods=['GET'])
def trigger_list():
    """List recent transcripts so you can pick a meeting_id to test with."""
    try:
        transcripts = fetch_recent_transcripts(10)
        rows = [{'id': t['id'], 'title': t.get('title'), 'date': t.get('date')}
                for t in transcripts]
        return jsonify({'transcripts': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/trigger/<meeting_id>', methods=['POST'])
def trigger_run(meeting_id):
    """Manually process a specific transcript. Test with:
       curl -X POST https://45-32-237-144.sslip.io/trigger/<meeting_id>
    """
    try:
        result = process_meeting(meeting_id)
        return jsonify({
            'status':        'ok',
            'meeting_title': result['title'],
            'docs':          result['docs'],
        }), 200
    except Exception as e:
        log.error('Manual trigger error: %s', e, exc_info=True)
        return jsonify({'error': str(e)}), 500


# ── Google OAuth (one-time setup, open in browser) ─────────────────────────────

@app.route('/auth/google')
def auth_google():
    if not CLIENT_SECRET_FILE:
        return 'client_secret JSON not found on this server.', 500
    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE),
        scopes=GOOGLE_SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
    )
    session['oauth_state'] = state
    return redirect(auth_url)


@app.route('/oauth/callback')
def oauth_callback():
    if not CLIENT_SECRET_FILE:
        return 'client_secret JSON not found.', 500
    state = session.get('oauth_state', '')
    flow  = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE),
        scopes=GOOGLE_SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI,
    )
    flow.fetch_token(authorization_response=request.url)
    _save_creds(flow.credentials)
    return 'Google account connected. You can close this tab.', 200


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
