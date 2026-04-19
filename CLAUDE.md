# AI Experts — Content & Website Project

## Purpose
Create content for the AI Experts website (YOUR_DOMAIN). Business: custom AI automations for recruiting agencies.

## Folder Structure

```
Business Website Creation/
├── .claude/skills/        ← ALL project skills live here (see Skills below)
├── content/drafts/        ← Raw content, outlines, and work in progress
├── blog/
│   ├── index.html         ← Blog listing (POSTS_START/POSTS_END markers for injection)
│   └── posts/{slug}/      ← Individual post folders (index.html + header.jpg)
├── linkedin/
│   ├── posts.json         ← LinkedIn post tracking (created, posted status)
│   ├── images/            ← Generated 4:5 LinkedIn visuals
│   └── post_to_linkedin.py ← OAuth + posting script
├── youtube/
│   ├── videos.json        ← YouTube video tracking (linked to LinkedIn post IDs)
│   ├── videos/            ← Per-video production folders ({post_id}/final_video.mp4 etc.)
│   ├── youtube_upload.py  ← Google OAuth + YouTube Data API upload script
│   └── youtube_token.pickle ← Cached OAuth token (do not delete)
├── invoice-app/           ← Flask invoice management dashboard
│   ├── app.py             ← Main Flask app (SQLAlchemy, PDF gen, email sending)
│   ├── deploy.sh          ← Deploy to /var/www/invoice/ on server
│   ├── invoice-app.service ← systemd unit file
│   ├── nginx.conf         ← Nginx config for invoice.YOUR_DOMAIN
│   ├── requirements.txt
│   ├── templates/         ← Jinja2 templates (dashboard, clients, invoices, PDF, etc.)
│   └── static/            ← app.js, style.css
├── imprint/index.html
├── privacy/index.html
├── index.html             ← Main landing page
├── generate_kie.py        ← kie.ai image generation helper script
├── get_kie_image.py       ← kie.ai image retrieval helper script
├── client_secret_*.json   ← Google OAuth client credentials (YouTube upload)
└── .env                   ← API keys and passwords (never commit)
```

### .env Variables

| Key | Purpose |
|---|---|
| `Password` | SSH/SCP server password for deploying the main site |
| `Stripe_API_Key` | Stripe integration (invoice app) |
| `KeyAI_API_KEY` | kie.ai API key for image generation |
| `Client_ID` | LinkedIn OAuth client ID |
| `Client_Secret` | LinkedIn OAuth client secret |
| `LinkedIn_Access_Token` | LinkedIn API access token |
| `YouTube_API_Key` | YouTube Data API key |
| `HeyGen_API_Key` | HeyGen API key for avatar video generation |
| `Avatar_ID` | HeyGen avatar ID |
| `MAIL_PASSWORD` | SMTP password for sending invoices via email |
| `EMAIL_ADDRESS` | Sender email (YOUR_WORK_EMAIL) |

## Skills

All skills live in `.claude/skills/`. Invoke with `/skill-name`.

| Skill | File | Purpose |
|---|---|---|
| `blog-post` | `.claude/skills/blog-post.md` | Write, generate image, and publish a full SEO blog post |
| `nano-banana-2` | `.claude/skills/nano-banana-2.md` | Generate images via kie.ai API |
| `frontend-design` | `.claude/skills/frontend-design.md` | Build production-grade UI components and pages |
| `seo-audit` | `.claude/skills/seo-audit.md` | Full website SEO audit with health score |
| `linkedin-post` | `.claude/skills/linkedin-post.md` | Turn latest blog post into 3 LinkedIn posts (text + visual) and publish one |
| `linkedin-avatar-video` | `.claude/skills/linkedin-avatar-video.md` | Turn a LinkedIn post into a HeyGen talking head video with B-roll, captions, and upload to YouTube |
| `content-pipeline` | `.claude/skills/content-pipeline.md` | Full content pipeline: asks Full Run or LinkedIn/YouTube only, then chains blog-post → linkedin-post → linkedin-avatar-video in sequence |

> **When a skill is added or changed, update this table immediately.**

## Key Context

### Server
- **Main site**: `root@YOUR_SERVER_IP`, web root `/var/www/aiexperts/`. Deploy via `sshpass` + `scp`. Password in `.env` as `Password`.
- **Invoice app**: same server, web root `/var/www/invoice/`. Deploy via `invoice-app/deploy.sh`. Domain: `invoice.YOUR_DOMAIN`.

### Design System (main site)
- Dark bg `#07070e`, gold accent `#c9a96e`, fonts Cormorant (headings) + Outfit (body), `fonts.css` self-hosted.

### Invoice App Stack
- Flask + SQLAlchemy (SQLite), ReportLab for PDF generation, SMTP email sending, Stripe integration, systemd service.

### Contacts & Social
- **Calendly**: https://calendly.com/dominik-limitless-ai-solutions/30min
- **Email**: YOUR_EMAIL
- **LinkedIn**: https://www.linkedin.com/company/limitless-ai-solutions-llc
- **Instagram**: https://www.instagram.com/germanaicreator

