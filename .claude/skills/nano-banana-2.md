---
name: nano-banana-2
description: Generate images using the Nano Banana 2 AI image model via the kie.ai API. Use this skill when the user asks to create, generate, or produce an image. Can be invoked standalone or called from other skills (e.g., blog-post).
---

This skill generates images using the **Nano Banana 2** model via the kie.ai API and saves them locally.

## How to Use

The user provides (or the calling skill passes):
- **Prompt** — descriptive text of the image to generate (be vivid and specific)
- **Output path** — where to save the image file (e.g., `/path/to/image.jpg`)
- **Aspect ratio** (optional) — `1:1`, `16:9`, `2:3`, `4:3`, `9:16`, or `auto` (default: `16:9` for blog headers, `1:1` for square)
- **Resolution** (optional) — `1K`, `2K`, or `4K` (default: `1K`)
- **Output format** (optional) — `jpg` or `png` (default: `jpg`)

## Steps to Execute

### 1. Read the API key from `.env`

Read the project `.env` file (located at `/Users/dominiks_mac/Business Website Creation/.env`) and extract the value of `KeyAI_API_KEY`.

```bash
grep 'KeyAI_API_KEY' "/Users/dominiks_mac/Business Website Creation/.env"
```

The key value is everything after `=`, stripped of surrounding quotes.

### 2. Create the image generation task

Make a POST request to the kie.ai API:

```bash
curl -s -X POST "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "nano-banana-2",
    "input": {
      "prompt": "YOUR_PROMPT_HERE",
      "aspect_ratio": "16:9",
      "resolution": "1K",
      "output_format": "jpg"
    }
  }'
```

Parse the `taskId` from the response: `response.data.taskId`

### 3. Poll for completion

Poll every 5 seconds until `state` is `"success"` or `"completed"` (max 60 attempts = 5 minutes):

```bash
curl -s "https://api.kie.ai/api/v1/jobs/recordInfo?taskId=TASK_ID" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Check `response.data.state`:
- `"success"` or `"completed"` → proceed to step 4
- `"failed"` or `"error"` → report error to user
- Any other state → wait 5 seconds and retry

### 4. Extract image URL and download

From the completed response, parse:
```
response.data.resultJson → parse as JSON → .resultUrls[0]
```

Then download the image:
```bash
curl -s -o "OUTPUT_PATH" "IMAGE_URL"
```

### 5. Confirm success

Report the saved path to the user (or to the calling skill) so it can be used further.

## Practical Example (Python script approach)

When doing multiple steps, use this inline Python script via Bash:

```python
import json, time, requests, sys

api_key = "READ_FROM_ENV"
prompt = "YOUR_PROMPT"
output_path = "OUTPUT_PATH"
aspect_ratio = "16:9"

headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
payload = {"model": "nano-banana-2", "input": {"prompt": prompt, "aspect_ratio": aspect_ratio, "resolution": "1K", "output_format": "jpg"}}

r = requests.post("https://api.kie.ai/api/v1/jobs/createTask", headers=headers, json=payload, timeout=30)
task_id = r.json()["data"]["taskId"]
print(f"Task ID: {task_id}")

for i in range(60):
    time.sleep(5)
    r = requests.get("https://api.kie.ai/api/v1/jobs/recordInfo", headers=headers, params={"taskId": task_id}, timeout=15)
    data = r.json().get("data", {})
    state = data.get("state", "")
    print(f"Poll {i+1}: {state}")
    if state in ("success", "completed"):
        urls = json.loads(data.get("resultJson", "{}")).get("resultUrls", [])
        img = requests.get(urls[0], timeout=30)
        with open(output_path, "wb") as f:
            f.write(img.content)
        print(f"Saved to {output_path}")
        sys.exit(0)
    elif state in ("failed", "error"):
        print("Generation failed"); sys.exit(1)

print("Timed out"); sys.exit(1)
```

Run this as a one-liner via `python3 -c "..."` or save to a temp file and execute.

## Prompt Writing Tips for Best Results

- Be highly descriptive and specific (lighting, mood, style, composition)
- For blog headers: use professional photography style, cinematic lighting, relevant subject matter
- Avoid faces/people if possible for cleaner professional images
- Include style cues: `"photorealistic"`, `"clean studio lighting"`, `"minimalist"`, `"dark dramatic lighting"`
- For AI/tech topics: think abstract data flows, glowing circuits, futuristic interfaces, robotic elements

## Notes

- The API key is stored in `.env` as `KeyAI_API_KEY`
- Model name must be exactly `"nano-banana-2"`
- Generation typically takes 30–90 seconds
- Images are downloaded and saved to the local file system
- Always confirm the output file exists after download before proceeding
