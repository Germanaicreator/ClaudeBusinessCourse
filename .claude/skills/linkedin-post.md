---
name: linkedin-post
description: Turn the latest blog post into 3 LinkedIn posts (text + visual) and post one unposted entry to LinkedIn. Tracks what has already been posted. Use when the user wants to repurpose a blog post as LinkedIn content or publish to LinkedIn.
---

This skill converts the latest AI Experts blog post into 3 LinkedIn posts (each with a 4:5 image) and posts the next unposted one to LinkedIn via the API.

## Business Context

- **LinkedIn Company Page**: https://www.linkedin.com/company/limitless-ai-solutions-llc
- **Target audience**: Recruiting agency owners, talent acquisition managers, HR tech decision-makers
- **Tone**: Relaxed but polished — think "smart practitioner sharing real insight", not corporate PR
- **Tracking file**: `/Users/dominiks_mac/Business Website Creation/linkedin/posts.json`
- **Images folder**: `/Users/dominiks_mac/Business Website Creation/linkedin/images/`
- **Post script**: `/Users/dominiks_mac/Business Website Creation/linkedin/post_to_linkedin.py`
- **Client credentials**: `Client_ID` and `Client_Secret` in `.env`

---

## Step 1 — Find the Latest Blog Post

Read the blog index to find the most recently published post:

```bash
# The first post card after POSTS_START is always the newest
grep -A2 'POSTS_START' "/Users/dominiks_mac/Business Website Creation/blog/index.html" | head -20
```

Or look at blog/posts/ directory timestamps:
```bash
ls -lt "/Users/dominiks_mac/Business Website Creation/blog/posts/"
```

Extract:
- **slug** — the post directory name (e.g., `eu-ai-act-recruiting-agencies`)
- **title** — from the post's `<h1 class="article-title">` tag
- **full content** — read the full `blog/posts/{slug}/index.html` to extract the article body

---

## Step 2 — Check if LinkedIn Posts Exist for this Slug

Read `/Users/dominiks_mac/Business Website Creation/linkedin/posts.json`.

Look for entries where `"blog_slug"` matches the latest post's slug.

**Case A — No posts exist yet for this slug**: Proceed to Step 3 (create posts).

**Case B — Posts exist**: Skip to Step 5 (find unposted and publish).

---

## Step 3 — Create 3 LinkedIn Posts (text only)

Based on the blog post content, write **3 distinct LinkedIn posts**. Each post targets business owners / recruiting agency leaders.

### Writing Rules
- **Hook**: First line must stop the scroll — a bold claim, a surprising stat, a provocative question, or a counterintuitive insight. No generic intros.
- **Body**: Useful, specific, actionable. Speak directly to the reader's pain or ambition. No fluff.
- **Style**: Conversational but polished. Short sentences. Line breaks between ideas. Feels like a knowledgeable founder sharing hard-won insight, not a blog being copy-pasted.
- **Length**: 150–250 words per post. LinkedIn sweet spot.
- **Hashtags**: 3–5 relevant hashtags at the end (e.g., `#AIAutomation #Recruiting #TalentAcquisition`)
- **Ending**: Always close with an open-ended question that invites replies (e.g., "What's the one task in your recruitment workflow you wish you could automate first?")
- **No markdown formatting in the text** — LinkedIn renders plain text only. Use line breaks, not bullet characters from markdown.

### Post Angles (one per post)

**Post 1 — The Core Insight**
Lead with the single most valuable / surprising insight from the article. What would make a recruiter stop scrolling? Build on it with 2–3 supporting points, then end with a question.

**Post 2 — Practical Tips / List**
Pull 3–5 concrete, actionable tips or takeaways from the article. Format as a short numbered list (use `1.` `2.` etc. in plain text). Frame each tip with a micro-explanation. End with a question.

**Post 3 — The Problem / Story Angle**
Open with a relatable pain point or scenario that recruiting agency owners face. Connect it to what AI automation can solve. Keep it story-like, not salesy. End with a question.

---

## Step 4 — Generate LinkedIn Images (4:5, 1080×1350 style)

Create one matching visual for each of the 3 posts using the **nano-banana-2** skill.

### Image Design System (apply consistently across ALL LinkedIn posts)

**Style**: Sleek, modern SaaS / B2B tech. Think Notion meets a high-end consulting firm's slide deck. Clean, not busy.

**Background**: Deep dark navy-to-black gradient (`#07070e` base). Subtle geometric grid lines in gold (`rgba(201,169,110,0.06)`). Optional soft glow/halo behind the central element.

**Central element**: One clear, simple illustration or icon-style graphic — NOT a photo. Options:
- An abstract diagram (flowchart, funnel, before/after split)
- A minimal icon with data points orbiting it
- A subtle 3D geometric shape with a tech overlay

**Typography in image**:
- **Title bar at the top** (always present): Short bold title (3–6 words max), gold accent color `#c9a96e`, Cormorant or similar serif font, placed on a dark semi-transparent bar at the top
- Keep any other text minimal and large enough to read on mobile

**NOT to include**: Busy charts, faces, stock-photography-style scenes, too much text, gradients that clash

**Aspect ratio**: `4:5` (portrait, ideal for LinkedIn feed). If the API doesn't support `4:5`, use `2:3`.

**Saving path**:
```
/Users/dominiks_mac/Business Website Creation/linkedin/images/{slug}-{post_number}.jpg
```
E.g.: `eu-ai-act-recruiting-agencies-1.jpg`, `eu-ai-act-recruiting-agencies-2.jpg`, `eu-ai-act-recruiting-agencies-3.jpg`

### Image Prompts (tailor per post)

For each of the 3 posts, write a prompt that matches the post's angle. Example structure:
```
Sleek modern SaaS illustration, dark navy background with subtle gold grid lines, [central element describing the post topic], minimal clean style, no text, cinematic soft lighting, ultra-sharp, professional B2B design aesthetic, 4:5 portrait format
```

Generate all 3 images before proceeding.

---

## Step 5 — Save Posts to Tracking File

After creating posts and images, update `/Users/dominiks_mac/Business Website Creation/linkedin/posts.json`.

**Structure**:
```json
{
  "posts": [
    {
      "id": "{slug}-1",
      "blog_slug": "{slug}",
      "blog_title": "Full Blog Post Title Here",
      "blog_url": "https://YOUR_DOMAIN/blog/posts/{slug}/",
      "post_number": 1,
      "angle": "core_insight",
      "text": "Full LinkedIn post text here...\n\n#Hashtag1 #Hashtag2",
      "image_path": "/Users/dominiks_mac/Business Website Creation/linkedin/images/{slug}-1.jpg",
      "posted": false,
      "posted_at": null,
      "linkedin_post_id": null,
      "created_at": "2026-04-15T00:00:00Z"
    }
  ]
}
```

Add all 3 new posts to the `"posts"` array (append — do not overwrite existing entries).

---

## Step 6 — Select the Next Unposted Post

From `posts.json`, find all entries where `"posted": false` for the current slug.

Pick the one with the **lowest `post_number`** (post 1 before post 2, etc.).

If all posts for this slug are already posted, report to the user:
> "All LinkedIn posts for '[slug]' have been published. Run the blog-post skill to create a new blog post first."

---

## Step 7 — Authenticate with LinkedIn (if needed)

Check `.env` for `LinkedIn_Access_Token`.

**If no token exists**, run the OAuth flow:
```bash
cd "/Users/dominiks_mac/Business Website Creation/linkedin"
python3 post_to_linkedin.py --auth
```
This opens a browser, starts a local server on port 3000, captures the OAuth callback, and saves the token to `.env`. Wait for the user to complete the browser login before continuing.

After auth, verify it works:
```bash
cd "/Users/dominiks_mac/Business Website Creation/linkedin"
python3 post_to_linkedin.py --me
```

**If a token exists**, proceed directly to Step 8.

---

## Step 8 — Post to LinkedIn

Run the posting script with the selected post's ID:

```bash
cd "/Users/dominiks_mac/Business Website Creation/linkedin"
python3 post_to_linkedin.py --post "{slug}-{post_number}"
```

The script will:
1. Load the post text and image path from `posts.json`
2. Upload the image to LinkedIn's media API
3. Create the post as the authenticated user
4. Mark the post as `"posted": true` with timestamp in `posts.json`

If the script exits with an error, check the error message:
- `401 Unauthorized` → token expired → re-run `--auth`
- `403 Forbidden` → missing scope → re-run `--auth` (re-authorize)
- Image upload errors → try posting without image (set `image_path` to null and re-run)

---

## Step 9 — Report to User

After successful posting, report:

```
LinkedIn post published!
- Post: [{slug}-{N}] — "{angle}"
- Blog post: {blog_url}
- Remaining unposted: {count} posts for this slug
- Next post ready: {next_post_id or "all done"}

Preview of what was posted:
---
{first 100 chars of post text}…
---
```

---

## Notes

- Always read the existing `posts.json` before writing — append, never overwrite
- The Python script (`post_to_linkedin.py`) is already written at `/Users/dominiks_mac/Business Website Creation/linkedin/post_to_linkedin.py`
- LinkedIn access tokens typically last 60 days — if auth fails, re-run `--auth`
- Images must be JPG or PNG, max 5 MB for LinkedIn
- The `posts.json` file is the single source of truth for what's been posted
