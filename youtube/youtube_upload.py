#!/usr/bin/env python3
"""
YouTube upload script for AI Experts avatar videos.
Usage: python3 youtube_upload.py <video_path> <title> <description> [tag1,tag2,...]

On first run a browser opens for OAuth — log in with germanaicreator@gmail.com.
A youtube_token.pickle is saved next to this script so future runs skip the browser.
"""

import os, pickle, sys, json
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import webbrowser

# ── Config ────────────────────────────────────────────────────────────────────
_HERE               = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(
    os.path.dirname(_HERE),
    "client_secret_630342337688-2sd7ujtmevbnn8d9quigt0mtjteuhtln.apps.googleusercontent.com.json"
)
TOKEN_FILE   = os.path.join(_HERE, "youtube_token.pickle")
SCOPES       = ["https://www.googleapis.com/auth/youtube.upload"]
REDIRECT_URI = "http://localhost:8080/"

# ── OAuth local callback handler ──────────────────────────────────────────────
_auth_code = None

class _OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2 style='font-family:sans-serif;margin:40px'>"
                b"Authentication successful! You can close this tab.</h2></body></html>"
            )
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing auth code.")

    def log_message(self, *args):
        pass  # suppress access logs


# ── Credential management ─────────────────────────────────────────────────────
def get_credentials():
    global _auth_code
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing token...")
            creds.refresh(Request())
        else:
            _auth_code = None
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,
            )
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )
            print(f"\nOpening browser for YouTube authentication...")
            print(f"If the browser does not open automatically, visit:\n{auth_url}\n")
            webbrowser.open(auth_url)

            server = HTTPServer(("localhost", 8080), _OAuthHandler)
            print("Waiting for OAuth callback on http://localhost:8080/ ...")
            while _auth_code is None:
                server.handle_request()
            server.server_close()

            flow.fetch_token(code=_auth_code)
            creds = flow.credentials

        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        print("Token saved to youtube_token.pickle")

    return creds


# ── Upload ────────────────────────────────────────────────────────────────────
def upload_video(video_path, title, description, tags=None):
    if not os.path.exists(video_path):
        print(f"ERROR: video file not found: {video_path}")
        sys.exit(1)

    size_mb = os.path.getsize(video_path) / 1024 / 1024
    print(f"Video: {os.path.basename(video_path)} ({size_mb:.1f} MB)")

    creds   = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title":       title[:100],        # YouTube limit
            "description": description[:5000],  # YouTube limit
            "tags":        tags or [],
            "categoryId":  "28",               # Science & Technology
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media   = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    print(f"Uploading...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  {pct}%", end="\r", flush=True)

    video_id = response["id"]
    url      = f"https://www.youtube.com/shorts/{video_id}"
    print(f"\nUploaded successfully!")
    print(f"URL: {url}")
    return video_id, url


# ── CLI entry ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 youtube_upload.py <video_path> <title> <description> [tag1,tag2,...]")
        sys.exit(1)

    video_path  = sys.argv[1]
    title       = sys.argv[2]
    description = sys.argv[3]
    tags        = sys.argv[4].split(",") if len(sys.argv) > 4 else []

    vid_id, url = upload_video(video_path, title, description, tags)
    print(json.dumps({"video_id": vid_id, "url": url}))
