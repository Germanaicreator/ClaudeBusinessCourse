#!/usr/bin/env python3
"""
LinkedIn posting script for AI Experts.

Usage:
  python3 post_to_linkedin.py --auth            OAuth flow — get access token
  python3 post_to_linkedin.py --post <post_id>  Post a specific post by ID
  python3 post_to_linkedin.py --me              Print the authenticated user URN
"""

import os
import sys
import json
import time
import threading
import webbrowser
import urllib.parse
import urllib.request
import http.server
import socketserver
import argparse
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
ENV_PATH  = BASE_DIR / ".env"
POSTS_PATH = Path(__file__).parent / "posts.json"

# ── Config ────────────────────────────────────────────────────────────────────
REDIRECT_URI  = "http://localhost:3000/callback"
AUTH_URL      = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL     = "https://www.linkedin.com/oauth/v2/accessToken"
API_BASE      = "https://api.linkedin.com/v2"
REST_BASE     = "https://api.linkedin.com/rest"
SCOPES        = "openid profile w_member_social"


# ── .env helpers ──────────────────────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def save_env_key(key: str, value: str):
    """Upsert a single key in the .env file."""
    content = ENV_PATH.read_text()
    lines = content.splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f'{key}="{value}"'
            updated = True
            break
    if not updated:
        lines.append(f'{key}="{value}"')
    ENV_PATH.write_text("\n".join(lines) + "\n")


# ── OAuth 2.0 ─────────────────────────────────────────────────────────────────
class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _CallbackHandler.code = params["code"][0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            b"<h2>Authentication successful! You can close this window.</h2>"
        )

    def log_message(self, *args):
        pass  # suppress logs


def run_auth_flow(client_id: str, client_secret: str):
    params = {
        "response_type": "code",
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPES,
        "state":         "aiexperts_linkedin",
    }
    auth_link = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print("\n── LinkedIn OAuth ───────────────────────────────────────────")
    print(f"Opening browser to:\n{auth_link}\n")
    print("Waiting for callback on http://localhost:3000/callback …")

    with socketserver.TCPServer(("", 3000), _CallbackHandler) as httpd:
        webbrowser.open(auth_link)
        # Serve until we get the code (max 120 s)
        httpd.timeout = 120
        for _ in range(120):
            httpd.handle_request()
            if _CallbackHandler.code:
                break

    code = _CallbackHandler.code
    if not code:
        print("ERROR: No code received within timeout.")
        sys.exit(1)

    print(f"Got authorization code. Exchanging for token …")
    data = urllib.parse.urlencode({
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  REDIRECT_URI,
        "client_id":     client_id,
        "client_secret": client_secret,
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read())

    access_token = token_data.get("access_token")
    if not access_token:
        print(f"ERROR: {token_data}")
        sys.exit(1)

    save_env_key("LinkedIn_Access_Token", access_token)
    print(f"\nAccess token saved to .env as LinkedIn_Access_Token")
    print("Run `python3 post_to_linkedin.py --me` to verify authentication.\n")


# ── API helpers ───────────────────────────────────────────────────────────────
def api_get(url: str, token: str, headers: dict = None) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_post(url: str, token: str, payload: dict, extra_headers: dict = None) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def get_person_urn(token: str) -> str:
    """Returns the authenticated person URN, e.g. 'urn:li:person:XXXXXXX'."""
    data = api_get(f"{API_BASE}/userinfo", token)
    return f"urn:li:person:{data['sub']}"


def upload_image(token: str, person_urn: str, image_path: str) -> str:
    """Upload an image and return the asset URN."""
    # Step 1: Register upload
    reg_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }
    reg_resp = api_post(
        f"{API_BASE}/assets?action=registerUpload",
        token, reg_payload
    )
    upload_url  = reg_resp["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn   = reg_resp["value"]["asset"]

    # Step 2: PUT the image bytes
    with open(image_path, "rb") as f:
        img_data = f.read()

    req = urllib.request.Request(upload_url, data=img_data, method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    content_type = "image/jpeg" if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg") else "image/png"
    req.add_header("Content-Type", content_type)
    with urllib.request.urlopen(req) as resp:
        pass  # 201 No Content

    return asset_urn


def create_post(token: str, person_urn: str, text: str, asset_urn: str = None) -> str:
    """Create a LinkedIn post. Returns the post URN."""
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE" if asset_urn else "NONE",
                **({"media": [{
                    "status": "READY",
                    "description": {"text": ""},
                    "media": asset_urn,
                    "title": {"text": ""}
                }]} if asset_urn else {})
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    resp = api_post(f"{API_BASE}/ugcPosts", token, payload)
    return resp.get("id", "")


# ── Tracking ──────────────────────────────────────────────────────────────────
def load_posts() -> dict:
    with open(POSTS_PATH) as f:
        return json.load(f)


def save_posts(data: dict):
    with open(POSTS_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Updated {POSTS_PATH}")


def mark_posted(post_id: str, linkedin_post_id: str):
    data = load_posts()
    for p in data["posts"]:
        if p["id"] == post_id:
            p["posted"] = True
            p["posted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            p["linkedin_post_id"] = linkedin_post_id
            break
    save_posts(data)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth", action="store_true", help="Run OAuth flow")
    parser.add_argument("--me",   action="store_true", help="Print user URN")
    parser.add_argument("--post", metavar="POST_ID", help="Post a specific post by ID")
    parser.add_argument("--list", action="store_true", help="List all posts and status")
    args = parser.parse_args()

    env = load_env()

    if args.auth:
        run_auth_flow(env["Client_ID"], env["Client_Secret"])
        return

    token = env.get("LinkedIn_Access_Token")
    if not token:
        print("No LinkedIn_Access_Token found. Run: python3 post_to_linkedin.py --auth")
        sys.exit(1)

    if args.me:
        urn = get_person_urn(token)
        print(f"Authenticated as: {urn}")
        return

    if args.list:
        data = load_posts()
        for p in data["posts"]:
            status = "POSTED" if p.get("posted") else "pending"
            print(f"  [{status}] {p['id']} — {p['blog_slug']} — {p.get('posted_at','')}")
        return

    if args.post:
        post_id = args.post
        data = load_posts()
        post = next((p for p in data["posts"] if p["id"] == post_id), None)
        if not post:
            print(f"ERROR: Post ID '{post_id}' not found in posts.json")
            sys.exit(1)
        if post.get("posted"):
            print(f"Post '{post_id}' is already posted ({post.get('posted_at')}). Aborting.")
            sys.exit(1)

        person_urn = get_person_urn(token)
        print(f"Posting as: {person_urn}")

        # Upload image if present
        asset_urn = None
        img_path = post.get("image_path")
        if img_path and Path(img_path).exists():
            print(f"Uploading image: {img_path}")
            asset_urn = upload_image(token, person_urn, img_path)
            print(f"Image asset: {asset_urn}")

        print("Creating post …")
        li_post_id = create_post(token, person_urn, post["text"], asset_urn)
        print(f"LinkedIn post ID: {li_post_id}")

        mark_posted(post_id, li_post_id)
        print(f"\nSuccessfully posted '{post_id}' to LinkedIn.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
