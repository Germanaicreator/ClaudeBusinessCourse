---
name: content-pipeline
description: Full content pipeline orchestrator. Runs blog-post, linkedin-post, and linkedin-avatar-video skills in sequence. Asks the user whether to do a Full Run (all three) or LinkedIn/YouTube only (skip blog creation). Use when the user wants to run the complete content workflow end-to-end.
---

This skill orchestrates the full AI Experts content pipeline in one go. It chains the individual skills together and asks the user upfront which mode to run.

## Step 1 — Ask the User Which Mode

Present this exact question before doing anything else:

> **Content Pipeline — which mode would you like to run?**
>
> **A) Full Run** — Create a new blog post, then turn it into a LinkedIn post + AI avatar YouTube Short
>
> **B) LinkedIn / YouTube only** — Skip blog creation, pick the next unposted LinkedIn post and turn it into a YouTube Short (and post a new LinkedIn post if needed)
>
> Type **A** or **B** to continue.

Wait for the user's response before proceeding.

---

## Mode A — Full Run

Run the following three skills **in sequence**, waiting for each to fully complete before starting the next.

### Phase 1 — Blog Post

Invoke the **blog-post** skill in full:
- Ask the user for a topic, URL, or raw information (as that skill specifies)
- Complete all steps through deployment (the blog post must be live on the server before continuing)

Once the blog post is live, inform the user:
> "Blog post published. Moving on to LinkedIn..."

### Phase 2 — LinkedIn Post

Invoke the **linkedin-post** skill in full:
- It will automatically detect the latest blog post (the one just published)
- Complete all steps: create 3 posts, generate 3 images, post the first unposted one to LinkedIn

Once the LinkedIn post is published, inform the user:
> "LinkedIn post published. Moving on to YouTube..."

### Phase 3 — Avatar Video

Invoke the **linkedin-avatar-video** skill in full:
- It will automatically pick the LinkedIn post just created (lowest `post_number` with `video_posted` not true)
- Complete all steps: script → HeyGen video → B-roll → captions → final video → YouTube upload → tracking update

---

## Mode B — LinkedIn / YouTube Only

Run the following two skills **in sequence**, waiting for each to fully complete before starting the next.

### Phase 1 — LinkedIn Post

Invoke the **linkedin-post** skill in full:
- Check `posts.json` for unposted entries
- If unposted entries exist for any slug: skip post creation, go straight to posting the next unposted one
- If all existing posts are posted: find the latest blog post, create 3 new posts + images for it, then post the first one
- Complete all steps through LinkedIn publishing

Once the LinkedIn post is published, inform the user:
> "LinkedIn post published. Moving on to YouTube..."

### Phase 2 — Avatar Video

Invoke the **linkedin-avatar-video** skill in full:
- It will automatically pick the next LinkedIn post where `video_posted` is false or missing
- Complete all steps: script → HeyGen video → B-roll → captions → final video → YouTube upload → tracking update

---

## Final Summary

After all phases complete, present a consolidated summary:

```
Content Pipeline Complete!

Mode: [Full Run / LinkedIn + YouTube Only]

────────────────────────────────────
BLOG POST (Full Run only)
  URL:      https://YOUR_DOMAIN/blog/posts/{slug}/
  Keyword:  {primary keyword}
  Words:    ~{word_count}

LINKEDIN
  Post ID:  {post_id}
  Angle:    {angle}
  Preview:  {first 80 chars}…

YOUTUBE SHORT
  URL:      {youtube_url}
  Duration: ~{duration}s
────────────────────────────────────

Next available LinkedIn post: {next_post_id or "none — run linkedin-post to create more"}
```

---

## Notes

- Always wait for each skill phase to fully complete before starting the next — the skills depend on each other's output (blog post → LinkedIn posts → video)
- In Mode B, if the linkedin-post skill reports "all posts already published", do NOT proceed to the video phase — inform the user and suggest running a Full Run or creating a new blog post first
- If any phase fails, stop and report the error clearly — do not attempt to continue to the next phase with incomplete data
- The pipeline is designed for one content piece per run; do not loop or batch multiple blog posts in a single run
