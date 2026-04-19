#!/usr/bin/env python3
"""
Skill Trigger Server — runs on your Mac at http://localhost:7777
Receives skill-launch requests from the Command Center browser UI,
executes `claude -p /skill-name` as a subprocess, and streams the
output live back to the browser via Server-Sent Events (SSE).

The LaunchAgent keeps this running automatically at login.
Log: ~/Library/Logs/skill-trigger.log
"""

import json
import os
import re
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

PROJECT_DIR    = "/Users/dominiks_mac/Business Website Creation"
SKILLS_DIR     = os.path.join(PROJECT_DIR, ".claude", "skills")
ALLOWED_ORIGIN = "https://controlcenter.YOUR_DOMAIN"

ALLOWED_SKILLS = {
    "content-pipeline",
    "blog-post",
    "linkedin-post",
    "linkedin-avatar-video",
}

# Preambles injected before skill content when the user provides input.
# They tell Claude the user already answered the first question so it
# should skip asking and proceed directly.
SKILL_INPUT_PREAMBLES = {
    "blog-post": (
        "The user has already provided the blog post topic — do NOT ask for it again, "
        "proceed directly to writing:\n\n"
        "Topic: {user_input}\n\n---\n\n"
    ),
    "content-pipeline": (
        "The user has already chosen the pipeline mode — do NOT ask again, "
        "proceed directly with that mode:\n\n"
        "Mode: {user_input}\n\n---\n\n"
    ),
}


def load_skill(skill_name: str, user_input: str = "") -> str:
    """Read skill file and optionally prepend the user's answer."""
    skill_file = os.path.join(SKILLS_DIR, f"{skill_name}.md")
    with open(skill_file, "r", encoding="utf-8") as f:
        content = f.read()
    # Strip YAML front-matter (--- ... ---) if present
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            content = content[end + 4:].lstrip()
    preamble = SKILL_INPUT_PREAMBLES.get(skill_name, "")
    if user_input.strip() and preamble:
        content = preamble.format(user_input=user_input.strip()) + content
    return content

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mABCDEFGHJKLMSTfhilrsu]')


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub('', text)


def find_claude():
    """Find the claude CLI binary."""
    # Check common locations first
    candidates = [
        shutil.which('claude'),
        os.path.expanduser('~/.claude/local/claude'),
        '/usr/local/bin/claude',
        '/opt/homebrew/bin/claude',
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # use our own logging

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        # ── Status ping ──────────────────────────────────────────────────────
        if path == '/status':
            claude = find_claude()
            body = json.dumps({
                "status": "online",
                "claude": claude or "not found",
            }).encode()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # ── SSE skill stream: GET /run/<skill_name>?input=<user_input> ─────────
        if path.startswith('/run/'):
            from urllib.parse import parse_qs
            skill      = path[5:].strip('/')
            qs         = parse_qs(parsed.query)
            user_input = qs.get('input', [''])[0]
            if skill not in ALLOWED_SKILLS:
                self.send_response(400)
                self._cors()
                self.end_headers()
                return
            self._stream_skill(skill, user_input)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        # Legacy POST /trigger — kept for fallback, just starts the SSE run
        parsed = urlparse(self.path)
        if parsed.path != '/trigger':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else b"{}"
        try:
            data  = json.loads(body)
            skill = data.get("skill", "").strip()
        except Exception:
            skill = ""

        if skill not in ALLOWED_SKILLS:
            resp = json.dumps({"error": f"Unknown skill: {skill}"}).encode()
            self.send_response(400)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)
            return

        resp = json.dumps({"ok": True, "stream": f"http://localhost:7777/run/{skill}"}).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)

    # ── SSE streaming ─────────────────────────────────────────────────────────
    def _stream_skill(self, skill: str, user_input: str = ""):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def send(event_type: str, data: dict):
            try:
                msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                self.wfile.write(msg.encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        claude = find_claude()
        if not claude:
            send("error", {"message": "claude CLI not found. Make sure Claude Code is installed."})
            send("done",  {"exit_code": 1})
            return

        # Load skill file content (with optional user input preamble)
        try:
            prompt = load_skill(skill, user_input)
        except FileNotFoundError:
            send("error", {"message": f"Skill file not found: {skill}.md"})
            send("done",  {"exit_code": 1})
            return

        send("start", {"skill": skill, "claude": claude})

        env = {**os.environ, "NO_COLOR": "1", "FORCE_COLOR": "0", "TERM": "dumb"}

        try:
            proc = subprocess.Popen(
                [claude, "--print", "--dangerously-skip-permissions", prompt],
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,
            )
        except Exception as e:
            send("error", {"message": f"Failed to start claude: {e}"})
            send("done",  {"exit_code": 1})
            return

        # Stream stdout line by line
        for raw_line in iter(proc.stdout.readline, ''):
            line = strip_ansi(raw_line).rstrip()
            send("line", {"text": line})

        # Flush any stderr
        stderr_out = proc.stderr.read()
        if stderr_out:
            for raw_line in stderr_out.splitlines():
                line = strip_ansi(raw_line).rstrip()
                if line:
                    send("line", {"text": line, "stderr": True})

        proc.wait()
        send("done", {"exit_code": proc.returncode})
        print(f"[trigger] /{skill} exited with code {proc.returncode}")


if __name__ == "__main__":
    port   = 7777
    server = HTTPServer(("127.0.0.1", port), Handler)
    claude = find_claude()
    print(f"  Skill Trigger Server  http://localhost:{port}")
    print(f"  claude binary: {claude or 'NOT FOUND — install Claude Code'}")
    print(f"  Project dir:   {PROJECT_DIR}")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("  Stopped.")
