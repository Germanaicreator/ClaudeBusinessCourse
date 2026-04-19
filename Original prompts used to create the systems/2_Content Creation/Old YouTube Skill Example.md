# YouTube Short Creator — Claude Code Channel

You are creating and posting a YouTube Short about Claude Code. Follow every step below in order. Do not skip steps. Announce each step before executing it.

**PROJECT_DIR**: `/Users/dominiks_mac/Faceless YouTube Project`

---

## STEP 1 — Check Past Reels

Read `$PROJECT_DIR/posted_reels.json`. List all previously posted titles and topics so you can avoid repeating them.

---

## STEP 2 — Fetch Claude Code Documentation

Use WebFetch to retrieve `https://code.claude.com/docs/en/overview`. Explore 1–2 linked sub-pages to build a full picture of available topics (hooks, MCP, CLAUDE.md, memory, sub-agents, skills, permissions, IDE integration, CLI flags, etc.).

---

## STEP 3 — Select a Topic

Choose ONE topic that:
- Has NOT been covered in any past reel (check Step 1)
- Is genuinely actionable and valuable for Claude Code users
- Can be taught in 30–60 seconds with 3–5 concrete, specific tips
- Is not too broad ("use Claude Code") or too narrow (a single obscure flag)

**Strongly prefer topics and title formulas from this proven high-performance list:**

| Title formula | Example | Why it works |
|---|---|---|
| "What Is [X]? The Simplest Explanation" | "What Is Claude Code?" | Targets beginners, high search volume |
| "[X] vs [Y] — What's Actually Different" | "Claude Code vs Claude.ai" | Comparison triggers high curiosity |
| "[Tool] Has a Secret [Feature]" | "Claude Code Has a Secret Planning Mode" | "Secret" creates intrigue |
| "Did [Company] Just [Dramatic Action]?" | "Did NVIDIA Just Cage Claude Code?" | News hook, controversy = clicks |
| "Stop [Wasting X] — N Simple Tricks" | "Stop Wasting Claude Credits — 4 Simple Tricks" | Problem + numbered solution |
| "[Event]: The [Thing] That Changed [Topic]" | "ClawHavoc: The Attack That Changed Claude Code Security" | Drama + stakes |
| "Use Multiple [Feature] at the Same Time" | "Use Multiple Claude Code Agents at the Same Time" | Power/scale appeal |

**Avoid these patterns — they consistently underperform:**
- Technical integration details (MCP setup, GitHub Actions YAML, Unix piping flags)
- Niche security comparisons without a clear dramatic hook
- Meta/self-referential content ("Claude Made This Video")
- Time-sensitive promos or announcements that expire
- Single-command tutorials with no narrative arc

**Announce the chosen topic** and explain why it's valuable before continuing.

---

## STEP 4 — Read the Writing Style Guide

Read `$PROJECT_DIR/writing_style_example.md` to internalize the exact script format, tone, and structure.

---

## STEP 5 — Write the Script

Write a YouTube Shorts script following the exact format from the writing style guide:

**Rules:**
- Total VO word count: **90–110 words maximum** (the Adam TTS voice reads at ~120wpm — stay under 110 words to keep the video under 60 seconds)
- Format: `(M:SS - M:SS) [IMAGE LABEL] VO: "spoken text"`
- Sections: INTRO (5s hook) → 3–5 PILLAR sections (~8s each) → OUTRO (5s CTA)
- VO text only — no timestamps or labels in the spoken text
- Each PILLAR = one specific, actionable tip with a concrete example (a real command, a real result)
- No buzzword shortcuts like "FIX:", "PRO TIP:", "INSTANTLY" — explain the concept in plain English

**Hook patterns that drive views — use one of these for the INTRO:**
- Direct question: "What is [X]?" (beginner hook — highest reach)
- Dramatic question: "Did [Company] just [shocking action]?" (news hook)
- Problem statement: "Running out of [resource]? These [N] tricks make it last longer." (relatable pain)
- Contrast setup: "[X] answers your questions. [Y] does the actual work." (comparison hook)
- Reveal tease: "By default, Claude Code [does X]. There is a smarter way." (secret/hidden feature hook)

**Outro must end with a single, immediate action** the viewer can take right now (e.g., "Type /plan before your next task", "Try /clear after your very next task").

Create `$PROJECT_DIR/current_production/` if it does not exist.

Save the full script to `$PROJECT_DIR/current_production/script.md`.

Save ONLY the spoken VO text (one line per section, no timestamps/labels) to `$PROJECT_DIR/current_production/vo_text.txt`.

After saving, count the total words in `vo_text.txt`. If over 110, trim before continuing.

---

## STEP 6 — Read Image Prompt Examples

Read all three JSON files from `$PROJECT_DIR/image_prompt_examples/` to understand the Nano Banana 2 prompt style.

---

## STEP 7 — Create Image Prompts

For each script section (INTRO + each PILLAR + OUTRO), create one JSON prompt file.

Each JSON must follow this exact structure:
```json
{
  "prompt": "A 9:16 futuristic circuit board aesthetic infographic on a dark near-black background with complex glowing cyan and orange PCB traces. [SPECIFIC VISUAL FOR THIS SECTION]. Huge, prominent neon text reads '[SECTION KEYWORD]' in bold glowing cyan letters. The entire composition is vertical 9:16 with intricate PCB traces and glowing circuit nodes throughout the dark background. Do not use photography. Do not add human faces. Render as a stylized tech infographic illustration.",
  "negative_prompt": "photography, photorealistic people, blurry text, illegible labels, low contrast, pastel colors, flat design, minimalist, white background, light background",
  "api_parameters": {
    "aspect_ratio": "9:16",
    "resolution": "1K",
    "output_format": "jpg"
  },
  "settings": {
    "style": "futuristic dark tech infographic, neon circuit board aesthetic",
    "lighting": "neon glow from circuit traces and data nodes",
    "quality": "high detail, sharp text, vibrant neon colors on dark background"
  }
}
```

Create `$PROJECT_DIR/current_production/prompts/` and save as `image_0.json` (INTRO), `image_1.json` (PILLAR 1), ... `image_N.json` (OUTRO).

---

## STEP 8 — Generate Images via Kie.ai

`generate_kie.py` reads its `.env` from one directory above itself (`/Users/dominiks_mac/.env`) and looks for `KIE_API_KEY`. Set this up first:

```bash
python3 - <<'EOF'
import re
with open('/Users/dominiks_mac/Faceless YouTube Project/.env') as f:
    for line in f:
        m = re.match(r'Kie_AI_API_KEY=["\']?([^"\'\n]+)', line)
        if m:
            with open('/Users/dominiks_mac/.env', 'w') as out:
                out.write(f'KIE_API_KEY="{m.group(1).strip()}"\n')
            print("Temp .env written")
EOF
```

Create `$PROJECT_DIR/current_production/images/`.

For each image (image_0 through image_N), run:
```bash
cd "/Users/dominiks_mac/Faceless YouTube Project" && python3 generate_kie.py \
  "current_production/prompts/image_N.json" \
  "current_production/images/image_N.jpg" \
  "9:16"
```

Run images one at a time (the script polls until completion — ~30–60s each). Retry once on failure.

After all images are done, clean up:
```bash
rm -f /Users/dominiks_mac/.env
```

---

## STEP 9 — Generate Voice Over via ElevenLabs

```bash
cd "/Users/dominiks_mac/Faceless YouTube Project" && python3 elevenlabs_tts.py \
  "current_production/vo_text.txt" \
  "current_production/voiceover.mp3" \
  "pNInz6obpgDQGcFmaJgB"
```

After generating, verify the duration:
```bash
/opt/homebrew/bin/ffprobe -v quiet -show_entries format=duration -of csv=p=0 \
  "/Users/dominiks_mac/Faceless YouTube Project/current_production/voiceover.mp3"
```

If the duration is **over 62 seconds**, trim `vo_text.txt` (remove the wordiest pillar or shorten each section) and regenerate. Target: 50–60 seconds.

If voice ID `pNInz6obpgDQGcFmaJgB` (Adam) fails, list voices and pick a male alternative:
```bash
cd "/Users/dominiks_mac/Faceless YouTube Project" && python3 elevenlabs_tts.py --list-voices
```

---

## STEP 10 — Check Whisper

```bash
python3 -c "import whisper; print('ok')" 2>/dev/null || pip3 install openai-whisper
```

---

## STEP 11 — Transcribe for Word-Level Timing

**Important**: Run Whisper as a Python module (not the `whisper` CLI command, which may not be on PATH):

```bash
python3 -m whisper \
  "/Users/dominiks_mac/Faceless YouTube Project/current_production/voiceover.mp3" \
  --model base --output_format json --word_timestamps True \
  --output_dir "/Users/dominiks_mac/Faceless YouTube Project/current_production/"
```

This creates `voiceover.json`. Now write and run `$PROJECT_DIR/current_production/parse_timing.py`:

```python
import json

with open("voiceover.json") as f:
    whisper_data = json.load(f)

# Collect all words with timestamps, stripping punctuation
all_words = []
for segment in whisper_data.get("segments", []):
    for w in segment.get("words", []):
        clean = w["word"].strip().lower().rstrip(".,!?;:")
        if clean:
            all_words.append({"word": clean, "start": w["start"], "end": w["end"]})

# Define section markers: the first distinctive words of each VO section
# ADAPT THESE to match the actual first words Whisper recognized for this script.
# Check the word list by printing all_words if markers don't match.
section_markers = [
    ("INTRO",    "image_0.jpg", ["<first_word_of_intro>"]),
    ("PILLAR 1", "image_1.jpg", ["<first_word_of_pillar1>"]),
    ("PILLAR 2", "image_2.jpg", ["<first_word_of_pillar2>"]),
    ("PILLAR 3", "image_3.jpg", ["<first_word_of_pillar3>"]),
    # Add more PILLARs if needed
    ("OUTRO",    "image_N.jpg", ["<two_unique_words_of_outro>"]),
]

def find_start(words, markers, from_idx=0):
    for i in range(from_idx, len(words) - len(markers) + 1):
        if all(words[i+j]["word"] == markers[j] for j in range(len(markers))):
            return i
    return None

timing = []
ptr = 0
for section_name, image_file, markers in section_markers:
    idx = find_start(all_words, markers, ptr)
    start_time = all_words[idx]["start"] if idx is not None else (timing[-1]["end"] if timing else 0.0)
    if idx is not None:
        ptr = idx + len(markers)
    timing.append({"section": section_name, "image": image_file, "start": round(start_time, 3), "end": None})

total = round(whisper_data["segments"][-1]["end"], 3)
for i in range(len(timing)):
    timing[i]["end"] = timing[i+1]["start"] if i+1 < len(timing) else total

for t in timing:
    print(f"{t['section']:12s} {t['start']:.2f}s -> {t['end']:.2f}s [{t['image']}]")

with open("timing.json", "w") as f:
    json.dump(timing, f, indent=2)
print("timing.json written.")
```

**Before writing section_markers**: first print the Whisper word list to see exactly how it transcribed the VO (words may differ from what was written — e.g. "@README" becomes "red meat"). Fill in the markers based on the actual transcription.

Run: `cd "$PROJECT_DIR/current_production" && python3 parse_timing.py`

Verify every section has a non-zero duration. If a section shows 0.0s, adjust its marker and re-run.

---

## STEP 12 — Create Caption Data

Write and run `$PROJECT_DIR/current_production/make_captions.py`:

```python
import json

with open("voiceover.json") as f:
    whisper_data = json.load(f)

all_words = []
for segment in whisper_data.get("segments", []):
    for w in segment.get("words", []):
        all_words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})

CHUNK_SIZE = 2
chunks = []
for i in range(0, len(all_words), CHUNK_SIZE):
    group = all_words[i:i + CHUNK_SIZE]
    chunks.append({"text": " ".join(w["word"] for w in group),
                   "start": group[0]["start"], "end": group[-1]["end"]})

with open("caption_chunks.json", "w") as f:
    json.dump(chunks, f, indent=2)
print(f"Wrote {len(chunks)} caption chunks.")
```

Run: `cd "$PROJECT_DIR/current_production" && python3 make_captions.py`

---

## STEP 13 — Build the Video

**Note**: The installed FFmpeg (v8.0.1) does NOT have libass or libfreetype — the `subtitles` and `drawtext` filters are unavailable. Use **moviepy** for the full video composition instead.

Write and run `$PROJECT_DIR/current_production/build_video.py`:

**Important**: Do NOT use MoviePy's `TextClip` — it causes caption cropping/clipping. Use the PIL-based `make_caption_clip()` below instead.

```python
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx import CrossFadeIn

with open("timing.json") as f:
    timing = json.load(f)
with open("caption_chunks.json") as f:
    caption_chunks = json.load(f)

W, H = 1080, 1920
FADE_DUR = 0.5
IMAGES_DIR = "images"

# Load audio first — its duration is the ground truth for total video length.
audio = AudioFileClip("voiceover.mp3")
total_dur = audio.duration
print(f"Audio duration (ground truth): {total_dur:.3f}s")

# Build image clips using timing.json durations
clips = []
for i, t in enumerate(timing):
    start = t["start"]
    end = t["end"] if i + 1 < len(timing) else total_dur
    dur = max(round(end - start, 3), 0.1)
    clip = ImageClip(os.path.join(IMAGES_DIR, t["image"])).resized((W, H)).with_duration(dur)
    clips.append(clip)

# Apply crossfades between clips
for i in range(1, len(clips)):
    clips[i] = clips[i].with_effects([CrossFadeIn(FADE_DUR)])

video = concatenate_videoclips(clips, method="compose", padding=-FADE_DUR)

# Sync video duration to audio
video_dur = video.duration
print(f"Video base duration after concat: {video_dur:.3f}s")
if video_dur < total_dur - 0.05:
    extra_dur = total_dur - video_dur + 0.1
    extra = ImageClip(os.path.join(IMAGES_DIR, timing[-1]["image"])).resized((W, H)).with_duration(extra_dur)
    video = concatenate_videoclips([video, extra], method="compose")
video = video.subclipped(0, total_dur)

# Attach audio
video = video.with_audio(audio)

# Find a bold system font
font_path = None
for fp in ["/System/Library/Fonts/Supplemental/Impact.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
           "/System/Library/Fonts/Helvetica.ttc"]:
    if os.path.exists(fp):
        font_path = fp
        break
print(f"Using font: {font_path}")

FONT_SIZE = 72
STROKE_WIDTH = 9
PAD = STROKE_WIDTH + 6

def make_caption_clip(text, font_path, font_size, stroke_width, pad, duration):
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = bbox[2] - bbox[0] + 2 * pad
    th = bbox[3] - bbox[1] + 2 * pad
    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text(
        (pad - bbox[0], pad - bbox[1]),
        text,
        font=font,
        fill="white",
        stroke_fill="black",
        stroke_width=stroke_width,
    )
    arr = np.array(img)
    clip = ImageClip(arr, is_mask=False).with_duration(duration)
    return clip

# Build caption clips using PIL (NOT TextClip)
text_clips = []
for chunk in caption_chunks:
    start, end = chunk["start"], min(chunk["end"], total_dur)
    dur = end - start
    if dur <= 0 or start >= total_dur:
        continue
    tc = make_caption_clip(chunk["text"], font_path, FONT_SIZE, STROKE_WIDTH, PAD, dur)
    y_pos = int(H * 0.62)
    text_clips.append(
        tc.with_start(start).with_position(("center", y_pos))
    )

# Composite and export
final = CompositeVideoClip([video] + text_clips, size=(W, H)).with_duration(total_dur)
final.write_videofile(
    "final_video.mp4", fps=30, codec="libx264", audio_codec="aac",
    ffmpeg_params=["-preset", "medium", "-crf", "23", "-b:a", "192k", "-ar", "44100"],
    logger="bar"
)
print(f"Done: final_video.mp4 ({os.path.getsize('final_video.mp4')/1024/1024:.1f} MB)")
```

Run: `cd "$PROJECT_DIR/current_production" && python3 build_video.py`

Rendering takes 1–3 minutes. If moviepy is not installed: `pip3 install moviepy`

---

## STEP 14 — Upload to YouTube

Derive the title and description:
- **Title**: Under 70 chars, punchy hook (e.g. "5 Claude Code Tricks That Save Hours")
- **Description**: 2–3 sentences + `#ClaudeCode #AITools #Productivity #CodingTips #YouTubeShorts`

```bash
cd "/Users/dominiks_mac/Faceless YouTube Project" && python3 youtube_upload.py \
  "current_production/final_video.mp4" \
  "<TITLE>" \
  "<DESCRIPTION>" \
  "Claude Code,AI Tools,Productivity,Coding Tips,YouTube Shorts"
```

**OAuth note**: A `youtube_token.pickle` is saved after the first login so future runs upload automatically without a browser. If the token expires or is missing, Chrome will open — log in with `elartistadelaluna@gmail.com` and grant YouTube upload permission.

---

## STEP 15 — Update the Posted Reels Log

Read `$PROJECT_DIR/posted_reels.json`, append to the `posted_reels` array:
```json
{
  "title": "<video title>",
  "topic": "<one sentence: what the video taught>",
  "date_posted": "<YYYY-MM-DD>",
  "youtube_url": "<URL from upload step>"
}
```
Write the updated JSON back to `$PROJECT_DIR/posted_reels.json`.

---

## STEP 16 — Archive Production Files

```bash
mkdir -p "/Users/dominiks_mac/Faceless YouTube Project/archive"
SAFE_TITLE=$(echo "<video_title>" | tr ' /:\\' '____' | cut -c1-50)
mv "/Users/dominiks_mac/Faceless YouTube Project/current_production" \
   "/Users/dominiks_mac/Faceless YouTube Project/archive/${SAFE_TITLE}_$(date +%Y%m%d)"
```

---

## DONE

Print a success summary:
```
✅ YouTube Short created and published!
Title:    <title>
URL:      <youtube_url>
Topic:    <topic>
Duration: ~<duration>s
Images:   <count> generated
```
