#!/usr/bin/env python3
"""
AI Experts — Email Analyzer & Auto-Responder
Polls Hostinger IMAP every 30 s for new emails, classifies them with
Azure OpenAI (gpt-4o-mini) and either moves spam to Junk, leaves
whitelisted / reply / YouTube-collab mails alone, or sends an
auto-reply to interested prospects including the Calendly link.

On the very first start (empty DB) all existing emails are skipped so
only truly NEW incoming mail is ever acted upon.
"""

import email
import email.utils
import imaplib
import json
import logging
import os
import re
import smtplib
import sqlite3
import time
from datetime import datetime
from email.header import decode_header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── ENV ───────────────────────────────────────────────────────────────────────

# .env: on the server it sits next to this script; locally it's one level up (repo root)
_env_local  = Path(__file__).parent / ".env"
_env_parent = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_local if _env_local.exists() else _env_parent)

# ── CONFIG ────────────────────────────────────────────────────────────────────

IMAP_HOST = "imap.hostinger.com"
IMAP_PORT = 993
SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 587

EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]   # Dominik@limitless-ai-solutions.com
EMAIL_PASSWORD = os.environ["MAIL_PASSWORD"]

AZURE_API_KEY     = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_ENDPOINT    = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
AZURE_DEPLOYMENT  = os.environ["AZURE_OPENAI_DEPLOYMENT"]
AZURE_API_VERSION = os.environ["AZURE_OPENAI_API_VERSION"]

BCC_ADDRESS   = "germanaicreator@gmail.com"
CALENDLY_LINK = "https://calendly.com/dominik-limitless-ai-solutions/30min"

COMPANY_EMAIL   = os.environ.get("COMPANY_EMAIL",   "Dominik@limitless-ai-solutions.com")
COMPANY_WEBSITE = os.environ.get("COMPANY_WEBSITE", "https://rosalia-yachts.com")

POLL_INTERVAL  = 30          # seconds between IMAP polls
BASE_DIR       = Path(__file__).parent
LOGO_PATH      = BASE_DIR / "logo.png"
WHITELIST_FILE = BASE_DIR / "whitelist.txt"
DB_PATH        = BASE_DIR / "email_analyzer.db"
LOG_PATH       = BASE_DIR / "email_analyzer.log"

# Hard-coded whitelist entries (always loaded even if file is absent)
HARDCODED_WHITELIST = {
    EMAIL_ADDRESS.lower(),
    BCC_ADDRESS.lower(),
}

# ── LOGGING ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_PATH),
    ],
)
log = logging.getLogger(__name__)

# ── DATABASE ─────────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            uid          TEXT NOT NULL,
            mailbox      TEXT NOT NULL DEFAULT 'INBOX',
            action       TEXT,
            processed_at TEXT,
            PRIMARY KEY (uid, mailbox)
        )
    """)
    con.commit()
    return con


def is_processed(con: sqlite3.Connection, uid: str, mailbox: str = "INBOX") -> bool:
    return con.execute(
        "SELECT 1 FROM processed_emails WHERE uid=? AND mailbox=?", (uid, mailbox)
    ).fetchone() is not None


def mark_processed(con: sqlite3.Connection, uid: str, action: str,
                   mailbox: str = "INBOX") -> None:
    con.execute(
        "INSERT OR IGNORE INTO processed_emails (uid, mailbox, action, processed_at) "
        "VALUES (?, ?, ?, ?)",
        (uid, mailbox, action, datetime.utcnow().isoformat()),
    )
    con.commit()


def is_first_run(con: sqlite3.Connection) -> bool:
    return con.execute("SELECT COUNT(*) FROM processed_emails").fetchone()[0] == 0

# ── WHITELIST ─────────────────────────────────────────────────────────────────

def load_whitelist() -> set:
    wl = set(HARDCODED_WHITELIST)
    if WHITELIST_FILE.exists():
        for line in WHITELIST_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                wl.add(line.lower())
    return wl

# ── IMAP HELPERS ─────────────────────────────────────────────────────────────

def imap_connect() -> imaplib.IMAP4_SSL:
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    log.info("IMAP: connected and logged in")
    return imap


def get_inbox_uids(imap: imaplib.IMAP4_SSL) -> list[bytes]:
    imap.select("INBOX")
    result, data = imap.uid("SEARCH", None, "ALL")
    if result != "OK" or not data[0]:
        return []
    return data[0].split()


def find_spam_folder(imap: imaplib.IMAP4_SSL) -> str:
    """Return the exact IMAP folder name for Junk/Spam on this server."""
    candidates = ["INBOX.Junk", "INBOX.Spam", "Junk", "Spam", "junk", "spam"]
    result, folders = imap.list()
    if result == "OK":
        # Parse the actual folder name from each LIST line, e.g.:
        # b'(\\HasNoChildren \\Junk) "." INBOX.Junk'  →  INBOX.Junk
        actual_folders = []
        for f in folders:
            line = f.decode() if isinstance(f, bytes) else f
            # Folder name is the last token (may be quoted)
            parts = line.rsplit(" ", 1)
            name = parts[-1].strip().strip('"')
            actual_folders.append(name)
        actual_lower = {n.lower(): n for n in actual_folders}
        for c in candidates:
            if c.lower() in actual_lower:
                return actual_lower[c.lower()]
    return "INBOX.Junk"   # Hostinger default


def move_to_spam(imap: imaplib.IMAP4_SSL, uid: bytes, spam_folder: str) -> None:
    result = imap.uid("COPY", uid, spam_folder)
    if result[0] == "OK":
        imap.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
        imap.expunge()
        log.info(f"UID {uid.decode()}: moved to {spam_folder}")
    else:
        # Fallback: just mark as read/flagged so user can review
        imap.uid("STORE", uid, "+FLAGS", "(\\Seen)")
        log.warning(f"UID {uid.decode()}: COPY to {spam_folder} failed — marked as read")

# ── EMAIL PARSING ─────────────────────────────────────────────────────────────

def decode_mime_words(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def get_email_body(msg: email.message.Message) -> str:
    """Extract the best plain-text body (first 4 000 chars for LLM context)."""
    text_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ct  = part.get_content_type()
            cd  = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload:
                    text_parts.append(payload.decode(charset, errors="replace"))
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            text_parts.append(payload.decode(charset, errors="replace"))

    body = "\n\n".join(text_parts)
    return body[:4000]

# ── AZURE OPENAI HELPERS ──────────────────────────────────────────────────────

def azure_chat(messages: list[dict], temperature: float = 0.2,
               max_tokens: int = 300) -> str:
    url = (
        f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}"
        f"/chat/completions?api-version={AZURE_API_VERSION}"
    )
    payload = {
        "messages":    messages,
        "temperature": temperature,
        "max_tokens":  max_tokens,
    }
    resp = requests.post(
        url,
        headers={"api-key": AZURE_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def classify_email(from_addr: str, subject: str, body: str) -> dict:
    """
    Returns dict with keys: category, language, reason
    category is one of: spam | youtube_collab | interested_client | other
    """
    system = (
        "You are an email classifier for Dominik, founder of an AI automation company "
        "that sells custom AI automations primarily to recruiting agencies.\n\n"
        "Classify each email into exactly ONE category and return VALID JSON ONLY — no markdown, no commentary.\n\n"
        "Categories:\n"
        "- \"spam\"             : newsletters, commercial promotions, payment-provider auto-notifications, "
        "generic sales outreach, subscription confirmations, marketing campaigns, cold sales pitches\n"
        "- \"youtube_collab\"   : a company or creator asking about a YouTube collaboration, sponsorship, "
        "or partnership on YouTube\n"
        "- \"interested_client\": a person or company clearly interested in hiring AI automation services, "
        "asking about pricing/scope, wanting to work together, or requesting a consultation\n"
        "- \"other\"            : anything that does not fit above (personal, unclear, technical, support)\n\n"
        "Return JSON: {\"category\": \"...\", \"language\": \"ISO-639-1 code\", "
        "\"reason\": \"one-sentence explanation\"}"
    )
    user = f"From: {from_addr}\nSubject: {subject}\n\nBody:\n{body}"

    raw = azure_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.1,
        max_tokens=200,
    )
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    log.warning(f"Could not parse classification JSON: {raw!r}")
    return {"category": "other", "language": "en", "reason": "parse error"}


def generate_reply(from_name: str, from_addr: str, subject: str,
                   body: str, language: str) -> str:
    """
    Ask the LLM to write a personalised, polite auto-reply in the correct language.
    The reply body ends exactly with the required sign-off lines.
    """
    lang_label = {
        "de": "German", "en": "English", "fr": "French", "es": "Spanish",
        "it": "Italian", "nl": "Dutch", "pt": "Portuguese", "pl": "Polish",
        "ro": "Romanian", "cs": "Czech", "hu": "Hungarian", "hr": "Croatian",
    }.get(language, language.upper())

    system = (
        f"You write professional, warm, and genuine email replies on behalf of Dominik, "
        f"founder of AI Experts — a company specialising in custom AI automation for recruiting agencies.\n\n"
        f"Write the reply body ONLY (no subject line, no To/From headers).\n"
        f"Write entirely in {lang_label}. Adapt the greeting to the person's name and cultural context.\n\n"
        f"The email must:\n"
        f"1. Open with an appropriate, personalised greeting.\n"
        f"2. Thank the person genuinely for reaching out.\n"
        f"3. Briefly acknowledge their interest and explain that the best next step is a free 30-minute strategy call.\n"
        f"4. Direct them to book via the Calendly link: {CALENDLY_LINK}\n"
        f"5. Be concise (3–4 short paragraphs). Warm and professional tone.\n"
        f"6. End with EXACTLY these lines (translate only if writing German, "
        f"otherwise keep English):\n\n"
        f"I am looking forward to speaking with you.\n"
        f"Best regards\n"
        f"Dominik\n\n"
        f"Do NOT add any signature block, contact info, or logo — those are added automatically."
    )
    user = (
        f"Original email from {from_name} <{from_addr}>:\n"
        f"Subject: {subject}\n\n{body}"
    )
    return azure_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.7,
        max_tokens=700,
    )

# ── EMAIL BUILDING ────────────────────────────────────────────────────────────

def build_reply_html(reply_text: str) -> str:
    """
    Wrap the LLM-generated reply text in a branded HTML email.
    Signature: plain text ending → logo (CID) → contact footer.
    """
    # Split on blank lines → paragraphs; preserve line-breaks within paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", reply_text) if p.strip()]
    body_html = "\n".join(
        f'<p style="margin:0 0 16px;font-size:15px;color:#333;line-height:1.6;">'
        f'{p.replace(chr(10), "<br>")}</p>'
        for p in paragraphs
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:40px 0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
  <table cellpadding="0" cellspacing="0" border="0" width="100%"
         style="max-width:600px;margin:0 auto;">
    <tr>
      <td style="background:#ffffff;border-radius:8px;padding:48px 48px 40px;
                 box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        {body_html}

        <!-- Calendly CTA button -->
        <table cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 32px;">
          <tr>
            <td style="border-radius:6px;background:#c9a96e;">
              <a href="{CALENDLY_LINK}"
                 style="display:inline-block;padding:13px 28px;color:#ffffff;
                        font-size:14px;font-weight:600;text-decoration:none;
                        font-family:Arial,Helvetica,sans-serif;">
                Book Your Free Strategy Call
              </a>
            </td>
          </tr>
        </table>

        <hr style="border:none;border-top:1px solid #e0e0e0;margin:0 0 24px;">

        <!-- Company logo (CID inline — Gmail-compatible) -->
        <img src="cid:company_logo" alt="AI Experts"
             style="height:52px;display:block;margin-bottom:16px;">

        <!-- Contact footer -->
        <p style="margin:0;font-size:12px;color:#999;line-height:1.7;">
          {COMPANY_EMAIL}<br>
          <a href="{COMPANY_WEBSITE}"
             style="color:#999;text-decoration:none;">{COMPANY_WEBSITE}</a>
        </p>

      </td>
    </tr>
  </table>
</body>
</html>"""


def send_auto_reply(to_addr: str, to_name: str, original_subject: str,
                    html_body: str, original_message_id: str = "") -> None:
    """Send the auto-reply via Hostinger SMTP with BCC to Dominik."""
    subject = (
        original_subject
        if original_subject.lower().startswith("re:")
        else f"Re: {original_subject}"
    )

    msg = MIMEMultipart("mixed")
    msg["From"]    = f"Dominik | AI Experts <{EMAIL_ADDRESS}>"
    msg["To"]      = f"{to_name} <{to_addr}>" if to_name else to_addr
    msg["Bcc"]     = BCC_ADDRESS
    msg["Subject"] = subject
    if original_message_id:
        msg["In-Reply-To"] = original_message_id
        msg["References"]  = original_message_id

    # related part: HTML + inline logo
    related = MIMEMultipart("related")
    related.attach(MIMEText(html_body, "html", "utf-8"))

    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as fh:
            logo_img = MIMEImage(fh.read(), _subtype="png")
        logo_img.add_header("Content-ID", "<company_logo>")
        logo_img.add_header("Content-Disposition", "inline", filename="logo.png")
        related.attach(logo_img)
    else:
        log.warning("logo.png not found — email will be sent without logo")

    msg.attach(related)

    recipients = [to_addr, BCC_ADDRESS]
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipients, msg.as_string())

# ── CORE PROCESSING ───────────────────────────────────────────────────────────

def process_single_email(imap: imaplib.IMAP4_SSL, con: sqlite3.Connection,
                         uid: bytes, whitelist: set, spam_folder: str) -> None:
    uid_str = uid.decode()

    # Fetch full RFC822 message
    result, data = imap.uid("FETCH", uid, "(RFC822)")
    if result != "OK" or not data or data[0] is None:
        log.warning(f"UID {uid_str}: fetch failed")
        mark_processed(con, uid_str, "fetch_error")
        return

    raw_bytes = data[0][1]
    msg = email.message_from_bytes(raw_bytes)

    # ── Parse key headers ────────────────────────────────────────────────────
    from_raw     = decode_mime_words(msg.get("From", ""))
    subject      = decode_mime_words(msg.get("Subject", "(no subject)"))
    message_id   = msg.get("Message-ID", "")
    in_reply_to  = msg.get("In-Reply-To", "").strip()
    references   = msg.get("References",  "").strip()

    from_name, from_addr = email.utils.parseaddr(from_raw)
    from_addr = from_addr.lower().strip()

    log.info(f"UID {uid_str}: From=<{from_addr}>  Subject={subject[:70]!r}")

    # ── 1. Whitelist ─────────────────────────────────────────────────────────
    if from_addr in whitelist:
        log.info(f"UID {uid_str}: whitelisted → skip")
        mark_processed(con, uid_str, "whitelisted")
        return

    # ── 2. Reply-to-outgoing detection ───────────────────────────────────────
    # Standard mail clients always set In-Reply-To on genuine replies.
    if in_reply_to or references:
        log.info(f"UID {uid_str}: has In-Reply-To/References → reply to outgoing, leave untouched")
        mark_processed(con, uid_str, "reply_to_outgoing")
        return

    # ── 3. Extract body for LLM ──────────────────────────────────────────────
    body = get_email_body(msg)

    # ── 4. Classify ──────────────────────────────────────────────────────────
    try:
        clf      = classify_email(from_addr, subject, body)
        category = clf.get("category", "other")
        language = clf.get("language", "en")
        reason   = clf.get("reason",   "")
        log.info(f"UID {uid_str}: category={category}  lang={language}  reason={reason}")
    except Exception as exc:
        log.error(f"UID {uid_str}: classification failed — {exc}")
        mark_processed(con, uid_str, "classification_error")
        return

    # ── 5. Act ───────────────────────────────────────────────────────────────
    if category == "spam":
        move_to_spam(imap, uid, spam_folder)
        mark_processed(con, uid_str, "moved_to_spam")

    elif category == "youtube_collab":
        log.info(f"UID {uid_str}: YouTube collab → leave untouched")
        mark_processed(con, uid_str, "youtube_collab_kept")

    elif category == "interested_client":
        log.info(f"UID {uid_str}: interested client → generating auto-reply …")
        try:
            reply_text = generate_reply(from_name, from_addr, subject, body, language)
            html_body  = build_reply_html(reply_text)
            send_auto_reply(from_addr, from_name, subject, html_body, message_id)
            log.info(f"UID {uid_str}: auto-reply sent to <{from_addr}>  BCC → {BCC_ADDRESS}")
            mark_processed(con, uid_str, "auto_replied")
        except Exception as exc:
            log.error(f"UID {uid_str}: failed to send auto-reply — {exc}")
            mark_processed(con, uid_str, "reply_error")

    else:  # "other"
        log.info(f"UID {uid_str}: other → leave untouched")
        mark_processed(con, uid_str, "other_kept")

    # Re-select INBOX after any folder operations
    imap.select("INBOX")

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────

def run() -> None:
    log.info("=" * 60)
    log.info("AI Experts Email Analyzer starting …")
    log.info(f"Monitoring: {EMAIL_ADDRESS}")
    log.info(f"Poll interval: {POLL_INTERVAL}s")
    log.info("=" * 60)

    con       = init_db()
    whitelist = load_whitelist()
    log.info(f"Whitelist: {len(whitelist)} address(es) loaded")

    while True:
        try:
            imap        = imap_connect()
            spam_folder = find_spam_folder(imap)
            log.info(f"Spam folder: {spam_folder}")

            # ── Startup: skip all existing emails on first ever run ──────────
            if is_first_run(con):
                uids = get_inbox_uids(imap)
                log.info(
                    f"First run detected — marking {len(uids)} existing email(s) as "
                    f"startup-skipped (no action taken)"
                )
                for uid in uids:
                    mark_processed(con, uid.decode(), "startup_skipped")
                log.info("Startup complete. Now watching for NEW incoming mail …")

            # ── Polling loop ─────────────────────────────────────────────────
            while True:
                try:
                    # Keep connection alive
                    imap.noop()
                except Exception:
                    log.warning("IMAP NOOP failed — reconnecting")
                    break

                uids     = get_inbox_uids(imap)
                new_uids = [u for u in uids if not is_processed(con, u.decode())]

                if new_uids:
                    log.info(f"Found {len(new_uids)} new email(s)")
                    for uid in new_uids:
                        try:
                            process_single_email(imap, con, uid, whitelist, spam_folder)
                        except Exception as exc:
                            log.error(f"UID {uid.decode()}: unexpected error — {exc}")
                            mark_processed(con, uid.decode(), "unexpected_error")
                        # Always re-select INBOX
                        try:
                            imap.select("INBOX")
                        except Exception:
                            break

                time.sleep(POLL_INTERVAL)

        except imaplib.IMAP4.error as exc:
            log.error(f"IMAP error: {exc} — reconnecting in 60 s")
            time.sleep(60)
        except ConnectionError as exc:
            log.error(f"Connection error: {exc} — reconnecting in 60 s")
            time.sleep(60)
        except KeyboardInterrupt:
            log.info("Shutting down.")
            break
        except Exception as exc:
            log.error(f"Unexpected top-level error: {exc} — reconnecting in 60 s")
            time.sleep(60)


if __name__ == "__main__":
    run()
