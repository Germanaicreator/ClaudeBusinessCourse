---
name: linkedin-avatar-video
description: Turn an unposted (as video) LinkedIn post into a 9:16 talking head AI avatar video using HeyGen, add B-roll images and captions, and publish to YouTube. Use when the user wants to repurpose LinkedIn posts as short-form video content.
---

This skill selects an unused LinkedIn post, writes a 30–45 second video script, generates a HeyGen talking head avatar video, overlays timed B-roll images, adds captions, assembles the final video with ffmpeg/moviepy, and uploads it to YouTube.

## File Paths & Credentials

- **LinkedIn posts**: `/Users/dominiks_mac/Business Website Creation/linkedin/posts.json`
- **Video output dir**: `/Users/dominiks_mac/Business Website Creation/youtube/videos/{post_id}/`
- **Video tracking**: `/Users/dominiks_mac/Business Website Creation/youtube/videos.json`
- **YouTube upload script**: `/Users/dominiks_mac/Business Website Creation/youtube/youtube_upload.py`
- **YouTube token**: `/Users/dominiks_mac/Business Website Creation/youtube/youtube_token.pickle`
- **Google OAuth secrets**: `/Users/dominiks_mac/Business Website Creation/client_secret_630342337688-2sd7ujtmevbnn8d9quigt0mtjteuhtln.apps.googleusercontent.com.json`
- **HeyGen API Key** (`.env`): `HeyGen_API_Key`
- **HeyGen Avatar ID** (`.env`): `Avatar_ID`
- **HeyGen Voice ID** (`.env`, optional): `HeyGen_Voice_ID` — if absent, the skill fetches the voice list and picks the first English voice
- **kie.ai API Key** (`.env`): `KeyAI_API_KEY`

---

## Step 1 — Select an Unposted (as video) LinkedIn Post

Read `/Users/dominiks_mac/Business Website Creation/linkedin/posts.json`.

Look for entries where `"video_posted"` is `false` **or the field does not exist**.

Pick the one with the **lowest `post_number`** across all eligible entries (post 1 before post 2, etc.).

If all posts have `"video_posted": true`, report:
> "All LinkedIn posts have already been turned into videos. Run the linkedin-post skill to generate more posts first."

Note the selected post's `id`, `text`, and any other relevant fields.

---

## Step 2 — Write the Video Script

Transform the selected LinkedIn post text into a spoken video script for the AI avatar.

**Rules:**
- **Length**: 75–115 words maximum (30–45 seconds at ~150 wpm)
- **Format**: Plain spoken text only — no titles, no labels, no markdown, no hashtags, no emojis, no "hook:", no stage directions
- **Tone**: Natural, conversational, direct — the avatar is talking to the camera like a knowledgeable founder sharing a quick insight
- **Structure**: Hook (5s) → 2–3 key points (~8s each) → short CTA close (~5s)
- **CTA close**: End with a soft call-to-action, e.g. "Book a free strategy call at YOUR_DOMAIN — link in bio."
- **No hashtags, no links mid-script** (they're unspoken)

Save the script to `{output_dir}/script.txt` (plain spoken text only).
Word-count it — if over 115 words, trim before continuing.

---

## Step 3 — Get HeyGen Voice ID (if needed)

Read `.env` and extract `HeyGen_Voice_ID`. If the variable is present and non-empty, skip this step.

If missing, fetch the voice list:

```bash
python3 - <<'EOF'
import requests, os, re

with open("/Users/dominiks_mac/Business Website Creation/.env") as f:
    env = {m.group(1): m.group(2).strip('"\'') for line in f
           if (m := re.match(r'(\w+)=["\']?([^"\'\n]+)', line))}

api_key = env["HeyGen_API_Key"]
r = requests.get("https://api.heygen.com/v2/voices",
                 headers={"X-Api-Key": api_key}, timeout=15)
voices = r.json().get("data", {}).get("voices", [])
en_voices = [v for v in voices if v.get("language", "").startswith("en")]
print("English voices found:")
for v in en_voices[:10]:
    print(f"  {v.get('voice_id')}  {v.get('display_name','')}")
EOF
```

Pick a natural-sounding English male/neutral voice (e.g. avoid obviously robotic ones) and note the `voice_id`. You will use this in Step 4.

---

## Step 4 — Generate the HeyGen Avatar Video

Set `prod_dir = /Users/dominiks_mac/Business Website Creation/youtube/videos/{post_id}` and create it:

```bash
mkdir -p "{prod_dir}"
```

Then generate the video:

```bash
python3 - <<'PYEOF'
import requests, re, time, os, sys

with open("/Users/dominiks_mac/Business Website Creation/.env") as f:
    env = {m.group(1): m.group(2).strip('"\'') for line in f
           if (m := re.match(r'(\w+)=["\']?([^"\'\n]+)', line))}

api_key  = env["HeyGen_API_Key"]
avatar_id = env["Avatar_ID"]
voice_id  = env.get("HeyGen_Voice_ID", "VOICE_ID_FROM_STEP_3")  # replace if needed

with open("{prod_dir}/script.txt") as f:
    script_text = f.read().strip()

headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
payload = {
    "video_inputs": [{
        "character": {
            "type": "avatar",
            "avatar_id": avatar_id,
            "avatar_style": "normal"
        },
        "voice": {
            "type": "text",
            "input_text": script_text,
            "voice_id": voice_id,
            "speed": 1.0
        }
    }],
    "dimension": {"width": 1080, "height": 1920}
}

r = requests.post("https://api.heygen.com/v2/video/generate",
                  headers=headers, json=payload, timeout=30)
data = r.json()
print("Create response:", data)
video_id = data.get("data", {}).get("video_id")
if not video_id:
    print("ERROR: no video_id in response"); sys.exit(1)
print(f"Video ID: {video_id}")

# Poll for completion (max 15 minutes)
for i in range(180):
    time.sleep(5)
    r = requests.get(f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
                     headers={"X-Api-Key": api_key}, timeout=15)
    status_data = r.json().get("data", {})
    status = status_data.get("status", "")
    print(f"Poll {i+1}: {status}")
    if status == "completed":
        video_url = status_data.get("video_url")
        print(f"Video URL: {video_url}")
        # Download
        vid = requests.get(video_url, timeout=120)
        with open("{prod_dir}/heygen_video.mp4", "wb") as f:
            f.write(vid.content)
        size_mb = os.path.getsize("{prod_dir}/heygen_video.mp4") / 1024 / 1024
        print(f"Downloaded heygen_video.mp4 ({size_mb:.1f} MB)")
        sys.exit(0)
    elif status == "failed":
        print("HeyGen generation FAILED:", status_data); sys.exit(1)

print("Timed out waiting for HeyGen video"); sys.exit(1)
PYEOF
```

**Important**: Replace `VOICE_ID_FROM_STEP_3` with the actual voice_id before running. After success, verify the file exists and is > 1 MB.

---

## Step 5 — Transcribe with Whisper

Install Whisper if needed:
```bash
python3 -c "import whisper; print('ok')" 2>/dev/null || pip3 install openai-whisper
```

Run transcription with word-level timestamps:
```bash
python3 -m whisper "{prod_dir}/heygen_video.mp4" \
  --model base --output_format json --word_timestamps True \
  --output_dir "{prod_dir}"
```

This creates `{prod_dir}/heygen_video.json`. Read it to see the full word-by-word transcript with timestamps.

Print all words with timestamps for inspection:
```bash
python3 - <<'EOF'
import json
with open("{prod_dir}/heygen_video.json") as f:
    data = json.load(f)
for seg in data["segments"]:
    for w in seg.get("words", []):
        print(f"{w['start']:.2f}s  {w['word']}")
EOF
```

---

## Step 6 — Plan B-Roll Segments

Based on the transcript and script content, decide on **2–3 B-roll image windows** that visually reinforce what the avatar is saying at that moment.

Rules:
- Each B-roll window: **minimum 2 seconds, maximum 5 seconds**
- Timing must not overlap between B-roll segments
- Leave the intro (first ~3s) and outro (last ~4s) as talking head only — no B-roll
- B-roll should appear during key factual or emotional moments, not during the CTA

Write a `{prod_dir}/broll_plan.json` with this structure:
```json
[
  {
    "index": 0,
    "start": 6.5,
    "end": 10.2,
    "description": "what this B-roll should visually show",
    "prompt": "Sleek dark tech illustration, [specific scene], ..."
  },
  {
    "index": 1,
    "start": 18.0,
    "end": 22.0,
    "description": "...",
    "prompt": "..."
  }
]
```

**B-roll image prompt style** (same dark design system used across the brand):
```
Sleek modern SaaS illustration, dark navy background (#07070e) with subtle gold grid lines, [central visual element relevant to the spoken point], minimalist clean style, no text, cinematic soft lighting, ultra-sharp, professional B2B design aesthetic, 9:16 vertical portrait format, photorealistic rendering
```

Avoid faces, stock-photo scenes, clashing gradients, or busy compositions.

---

## Step 7 — Generate B-Roll Images (nano-banana-2)

For each entry in `broll_plan.json`, generate a 9:16 image using the **nano-banana-2** skill logic:

```python
import json, time, requests, sys, re

with open("/Users/dominiks_mac/Business Website Creation/.env") as f:
    env = {m.group(1): m.group(2).strip('"\'') for line in f
           if (m := re.match(r'(\w+)=["\']?([^"\'\n]+)', line))}

api_key = env["KeyAI_API_KEY"]
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

with open("{prod_dir}/broll_plan.json") as f:
    broll_plan = json.load(f)

for broll in broll_plan:
    idx = broll["index"]
    output_path = f"{prod_dir}/broll_{idx}.jpg"
    payload = {
        "model": "nano-banana-2",
        "input": {
            "prompt": broll["prompt"],
            "aspect_ratio": "9:16",
            "resolution": "1K",
            "output_format": "jpg"
        }
    }
    r = requests.post("https://api.kie.ai/api/v1/jobs/createTask",
                      headers=headers, json=payload, timeout=30)
    task_id = r.json()["data"]["taskId"]
    print(f"B-roll {idx}: task {task_id}")

    for poll in range(60):
        time.sleep(5)
        r = requests.get("https://api.kie.ai/api/v1/jobs/recordInfo",
                         headers=headers, params={"taskId": task_id}, timeout=15)
        data = r.json().get("data", {})
        state = data.get("state", "")
        print(f"  Poll {poll+1}: {state}")
        if state in ("success", "completed"):
            urls = json.loads(data.get("resultJson", "{}")).get("resultUrls", [])
            img = requests.get(urls[0], timeout=30)
            with open(output_path, "wb") as f:
                f.write(img.content)
            print(f"  Saved broll_{idx}.jpg")
            break
        elif state in ("failed", "error"):
            print(f"  B-roll {idx} generation failed"); sys.exit(1)
    else:
        print(f"  B-roll {idx} timed out"); sys.exit(1)

print("All B-roll images downloaded.")
```

Verify each `broll_{idx}.jpg` exists and is > 10 KB before continuing.

---

## Step 8 — Create Caption Data

Write and run `{prod_dir}/make_captions.py`:

```python
import json

with open("{prod_dir}/heygen_video.json") as f:
    whisper_data = json.load(f)

all_words = []
for segment in whisper_data.get("segments", []):
    for w in segment.get("words", []):
        all_words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})

# 2-word chunks — matches caption style from brand playbook
CHUNK_SIZE = 2
chunks = []
for i in range(0, len(all_words), CHUNK_SIZE):
    group = all_words[i:i + CHUNK_SIZE]
    chunks.append({
        "text": " ".join(w["word"] for w in group),
        "start": group[0]["start"],
        "end": group[-1]["end"]
    })

with open("{prod_dir}/captions.json", "w") as f:
    json.dump(chunks, f, indent=2)
print(f"Wrote {len(chunks)} caption chunks.")
```

Run: `cd "{prod_dir}" && python3 make_captions.py`

---

## Step 9 — Assemble the Final Video

Install moviepy if needed: `pip3 install moviepy`

Write and run `{prod_dir}/build_video.py`:

```python
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from moviepy.video.fx import CrossFadeIn, FadeOut

# ── Load base talking-head video ────────────────────────────────────────────
base = VideoFileClip("{prod_dir}/heygen_video.mp4")
W, H = base.size   # expected 1080×1920
total_dur = base.duration
print(f"Base video: {W}x{H}, {total_dur:.2f}s")

# Resize if HeyGen delivered different dimensions
if (W, H) != (1080, 1920):
    base = base.resized((1080, 1920))
    W, H = 1080, 1920

# ── Load plans ───────────────────────────────────────────────────────────────
with open("{prod_dir}/broll_plan.json") as f:
    broll_plan = json.load(f)
with open("{prod_dir}/captions.json") as f:
    caption_chunks = json.load(f)

# ── Build B-roll overlay clips ───────────────────────────────────────────────
# B-roll images appear as full-screen overlays on top of the talking head,
# with 0.2s fade-in and 0.2s fade-out.
BROLL_FADE = 0.2
overlay_clips = []
for broll in broll_plan:
    start = broll["start"]
    end   = broll["end"]
    dur   = round(end - start, 3)
    if dur < 0.5:
        print(f"Skipping B-roll {broll['index']}: duration too short ({dur}s)")
        continue
    img_path = f"{prod_dir}/broll_{broll['index']}.jpg"
    clip = (ImageClip(img_path)
            .resized((W, H))
            .with_duration(dur)
            .with_effects([CrossFadeIn(BROLL_FADE), FadeOut(BROLL_FADE)])
            .with_start(start))
    overlay_clips.append(clip)
    print(f"B-roll {broll['index']}: {start:.2f}s → {end:.2f}s")

# ── Caption clips (PIL-based, never TextClip) ─────────────────────────────────
font_path = None
for fp in [
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]:
    if os.path.exists(fp):
        font_path = fp
        break
print(f"Caption font: {font_path}")

FONT_SIZE    = 72
STROKE_WIDTH = 9
PAD          = STROKE_WIDTH + 6

def make_caption_clip(text, font_path, font_size, stroke_width, pad, duration):
    font  = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox  = dummy.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw    = bbox[2] - bbox[0] + 2 * pad
    th    = bbox[3] - bbox[1] + 2 * pad
    img   = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)
    draw.text(
        (pad - bbox[0], pad - bbox[1]),
        text,
        font=font,
        fill="white",
        stroke_fill="black",
        stroke_width=stroke_width,
    )
    arr = np.array(img)
    return ImageClip(arr, is_mask=False).with_duration(duration)

text_clips = []
for chunk in caption_chunks:
    start = chunk["start"]
    end   = min(chunk["end"], total_dur)
    dur   = end - start
    if dur <= 0 or start >= total_dur:
        continue
    tc = make_caption_clip(chunk["text"], font_path, FONT_SIZE, STROKE_WIDTH, PAD, dur)
    y_pos = int(H * 0.62)
    text_clips.append(tc.with_start(start).with_position(("center", y_pos)))

# ── Composite: base + B-roll overlays + captions ─────────────────────────────
# Layer order: base video → B-roll overlays → captions (always on top)
all_clips = [base] + overlay_clips + text_clips
final = CompositeVideoClip(all_clips, size=(W, H)).with_duration(total_dur)

final.write_videofile(
    "{prod_dir}/final_video.mp4",
    fps=30,
    codec="libx264",
    audio_codec="aac",
    ffmpeg_params=["-preset", "medium", "-crf", "23", "-b:a", "192k", "-ar", "44100"],
    logger="bar"
)
size_mb = os.path.getsize("{prod_dir}/final_video.mp4") / 1024 / 1024
print(f"Done: final_video.mp4 ({size_mb:.1f} MB)")
```

Run: `python3 "{prod_dir}/build_video.py"`

Rendering takes 1–5 minutes. Verify `final_video.mp4` exists and is > 1 MB before continuing.

---

## Step 10 — Ensure YouTube Upload Script Exists

Check if `/Users/dominiks_mac/Business Website Creation/youtube/youtube_upload.py` exists. If not, create it:

```python
#!/usr/bin/env python3
"""YouTube upload script for AI Experts avatar videos."""

import os, pickle, sys, json
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import webbrowser

CLIENT_SECRETS_FILE = "/Users/dominiks_mac/Business Website Creation/client_secret_630342337688-2sd7ujtmevbnn8d9quigt0mtjteuhtln.apps.googleusercontent.com.json"
TOKEN_FILE          = "/Users/dominiks_mac/Business Website Creation/youtube/youtube_token.pickle"
SCOPES              = ["https://www.googleapis.com/auth/youtube.upload"]
REDIRECT_URI        = "http://localhost:8080/"

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
            self.wfile.write(b"<h2>Authentication successful! You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing auth code.")
    def log_message(self, *args):
        pass  # suppress request logs

def get_credentials():
    global _auth_code
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            _auth_code = None
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
            )
            auth_url, _ = flow.authorization_url(
                access_type="offline", include_granted_scopes="true", prompt="consent"
            )
            print(f"\nOpening browser for YouTube authentication...")
            print(f"If browser does not open, visit:\n{auth_url}\n")
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
        print("Token saved.")
    return creds

def upload_video(video_path, title, description, tags=None):
    creds   = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title":       title,
            "description": description,
            "tags":        tags or [],
            "categoryId":  "28",  # Science & Technology
        },
        "status": {"privacyStatus": "public"},
    }
    media   = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    print(f"Uploading {os.path.basename(video_path)}...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%")
    video_id = response["id"]
    url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"Uploaded! {url}")
    return video_id, url

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: youtube_upload.py <video_path> <title> <description> [tag1,tag2,...]")
        sys.exit(1)
    path        = sys.argv[1]
    title       = sys.argv[2]
    description = sys.argv[3]
    tags        = sys.argv[4].split(",") if len(sys.argv) > 4 else []
    vid_id, url = upload_video(path, title, description, tags)
    print(json.dumps({"video_id": vid_id, "url": url}))
```

Install required packages if needed:
```bash
pip3 install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## Step 11 — Upload to YouTube

Derive the title and description from the script and original LinkedIn post:

- **Title**: Under 70 characters. Hook-driven. E.g. "EU AI Act: What Every Recruiting Agency Must Know" or "3 AI Compliance Rules Recruiting Agencies Miss"
- **Description**: 2–3 sentences summarising the video + the business CTA + relevant hashtags
  ```
  {2–3 sentence summary of the video content}

  👉 Book a free AI automation strategy call: https://calendly.com/dominik-limitless-ai-solutions/30min

  #AIAutomation #RecruitingAgencies #AICompliance #TalentAcquisition #HRTech
  ```
- **Tags**: `AIAutomation,RecruitingAgencies,TalentAcquisition,HRTech,AICompliance,Recruiting,ArtificialIntelligence`

Run:
```bash
python3 "/Users/dominiks_mac/Business Website Creation/youtube/youtube_upload.py" \
  "{prod_dir}/final_video.mp4" \
  "TITLE_HERE" \
  "DESCRIPTION_HERE" \
  "AIAutomation,RecruitingAgencies,TalentAcquisition,HRTech"
```

**OAuth note**: On first run, a browser opens. Log in with `YOUR_EMAIL` and grant YouTube upload permission. A `youtube_token.pickle` is saved so future runs skip the browser step.

Capture the returned YouTube URL (format: `https://www.youtube.com/shorts/{video_id}`).

---

## Step 12 — Update Tracking

### Update `linkedin/posts.json`

Read the file, find the matching post entry by `id`, and add/update these fields:
```json
{
  "video_posted": true,
  "video_posted_at": "2026-04-15T12:00:00Z",
  "youtube_url": "https://www.youtube.com/shorts/VIDEO_ID"
}
```

Write the updated JSON back (never overwrite other entries).

### Update (or create) `youtube/videos.json`

Read the file (or create it if missing with `{"videos": []}`). Append:
```json
{
  "linkedin_post_id": "{post_id}",
  "title": "Video title",
  "youtube_url": "https://www.youtube.com/shorts/VIDEO_ID",
  "script_path": "{prod_dir}/script.txt",
  "final_video_path": "{prod_dir}/final_video.mp4",
  "published_at": "2026-04-15T12:00:00Z"
}
```

---

## Step 13 — Report to User

```
Avatar video published to YouTube!

LinkedIn post:  {post_id} — "{angle}"
Script length:  ~{word_count} words (~{duration}s)
B-roll images:  {count} overlays
YouTube URL:    {youtube_url}

Script preview:
---
{first 120 chars of script}…
---
```

---

## Notes

- Always verify `final_video.mp4` exists and is > 1 MB before uploading to YouTube
- The base video from HeyGen is 1080×1920 (9:16) — if dimensions differ, the build script resizes automatically
- Caption position is at 62% of frame height (y = int(H * 0.62)) — same style as the brand's YouTube Short playbook
- B-roll images fully overlay the talking head during their window; the avatar audio continues underneath
- `youtube_token.pickle` persists between runs — no browser login after first authorisation
- If HeyGen returns `status: failed`, check the API response for error details and retry once
- If Whisper transcribes `@` symbols or odd artifacts, clean the word list before building captions
- On Macs without libass/libfreetype in system ffmpeg, moviepy's PIL-based captions are the correct approach (do NOT use `drawtext` filter or `TextClip`)
