import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from moviepy.video.fx import CrossFadeIn, FadeOut

PROD = "/Users/dominiks_mac/Business Website Creation/youtube/videos/eu-ai-act-recruiting-agencies-1"

# ── Load base talking-head video ─────────────────────────────────────────────
print("Loading HeyGen base video...")
base = VideoFileClip(f"{PROD}/heygen_video.mp4")
W, H = base.size
total_dur = base.duration
print(f"Base video: {W}x{H}, {total_dur:.2f}s")

if (W, H) != (1080, 1920):
    print(f"Resizing from {W}x{H} to 1080x1920")
    base = base.resized((1080, 1920))
    W, H = 1080, 1920

# ── Load plans ───────────────────────────────────────────────────────────────
with open(f"{PROD}/broll_plan.json") as f:
    broll_plan = json.load(f)
with open(f"{PROD}/captions.json") as f:
    caption_chunks = json.load(f)

# ── Build B-roll overlay clips ───────────────────────────────────────────────
BROLL_FADE = 0.2
overlay_clips = []
for broll in broll_plan:
    start = broll["start"]
    end   = broll["end"]
    dur   = round(end - start, 3)
    if dur < 0.5:
        print(f"Skipping B-roll {broll['index']}: too short ({dur}s)")
        continue
    img_path = f"{PROD}/broll_{broll['index']}.jpg"
    clip = (ImageClip(img_path)
            .resized((W, H))
            .with_duration(dur)
            .with_effects([CrossFadeIn(BROLL_FADE), FadeOut(BROLL_FADE)])
            .with_start(start))
    overlay_clips.append(clip)
    print(f"B-roll {broll['index']}: {start:.2f}s → {end:.2f}s ({dur:.2f}s)")

# ── Caption style (same as brand playbook) ───────────────────────────────────
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
    tc    = make_caption_clip(chunk["text"], font_path, FONT_SIZE, STROKE_WIDTH, PAD, dur)
    y_pos = int(H * 0.62)
    text_clips.append(tc.with_start(start).with_position(("center", y_pos)))

print(f"Built {len(text_clips)} caption clips")

# ── Composite: base + B-roll overlays + captions ─────────────────────────────
print("Compositing...")
all_clips = [base] + overlay_clips + text_clips
final = CompositeVideoClip(all_clips, size=(W, H)).with_duration(total_dur)

out = f"{PROD}/final_video.mp4"
print(f"Rendering to {out} ...")
final.write_videofile(
    out,
    fps=30,
    codec="libx264",
    audio_codec="aac",
    ffmpeg_params=["-preset", "medium", "-crf", "23", "-b:a", "192k", "-ar", "44100"],
    logger="bar"
)
size_mb = os.path.getsize(out) / 1024 / 1024
print(f"\nDone: final_video.mp4 ({size_mb:.1f} MB)")
