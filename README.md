# AI Experts Business Suite

A complete, Claude Code–built business tech stack for an example solo AI automation consultancy — built live as part of a video course by **Dominik Pascal Felber (Germanaicreator)**.

This repository contains every system built during the course: the main website, blog, invoice dashboard, proposal generator, LinkedIn automation, YouTube pipeline, email analyzer, PII cleaner, and a business command center — all deployable to a single Linux VPS.

---

## What's Inside

| Folder | What it does |
|---|---|
| `index.html` | Main landing page (dark design, Cormorant + Outfit fonts) |
| `blog/` | Blog listing + individual post pages |
| `invoice-app/` | Flask invoice dashboard with PDF generation + email sending |
| `proposal-app/` | Proposal & contract generator (Fireflies + Azure OpenAI + Google Docs) |
| `command-center/` | Central dashboard linking all apps (SSO, media browser) |
| `email-analyzer/` | AI-powered email analysis and triage tool |
| `pii-cleaner/` | PII detection and redaction tool (Azure OpenAI) |
| `linkedin/` | LinkedIn post tracker + OAuth posting script |
| `youtube/` | YouTube video tracker + upload script (Google OAuth) |
| `content/` | Raw drafts and content outlines |
| `.claude/skills/` | Custom Claude Code skills (blog, LinkedIn, video pipeline) |
| `Original Claude Code Prompts/` | The exact prompts used to build each system (added manually) |

---

## Prerequisites

- A VPS (Ubuntu 22.04+ recommended) with `root` access
- A domain name pointed at your server
- Python 3.10+, `sshpass`, `nginx`, `certbot` on the server
- Accounts for: Stripe, LinkedIn, YouTube/Google, HeyGen, Azure OpenAI, kie.ai, Fireflies

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Germanaicreator/ClaudeBusinessCourse.git
cd ClaudeBusinessCourse
```

### 2. Configure your environment

```bash
cp .env.example .env
```

Open `.env` and fill in **all** placeholder values (API keys, server IP, passwords).

### 3. Update placeholders in deploy scripts

Search for `YOUR_SERVER_IP`, `YOUR_DOMAIN`, `YOUR_EMAIL`, and `YOUR_WORK_EMAIL` across the repo and replace them with your actual values:

```bash
grep -r "YOUR_SERVER_IP\|YOUR_DOMAIN\|YOUR_EMAIL" . --include="*.sh" --include="*.conf" --include="*.md" -l
```

### 4. Deploy individual apps

Each app has its own `deploy.sh`. Run from the project root after filling in `.env`:

```bash
# Invoice Dashboard
bash invoice-app/deploy.sh

# Proposal & Contract Generator
bash proposal-app/deploy.sh

# Business Command Center
bash command-center/deploy.sh

# Email Analyzer
bash email-analyzer/deploy.sh
```

Each script will:
- Upload code to your server via `scp`
- Create a Python virtual environment
- Install dependencies
- Configure a `systemd` service
- Set up Nginx with SSL (via Certbot)

### 5. Use Claude Code skills

This project includes custom Claude Code skills in `.claude/skills/`. Open the project in Claude Code and invoke them:

| Command | What it does |
|---|---|
| `/blog-post` | Research, write, generate image, and publish a full SEO blog post |
| `/linkedin-post` | Turn the latest blog post into 3 LinkedIn drafts + publish one |
| `/linkedin-avatar-video` | Turn a LinkedIn post into a HeyGen talking-head video + upload to YouTube |
| `/content-pipeline` | Run the full blog → LinkedIn → YouTube pipeline in sequence |
| `/nano-banana-2` | Generate images via kie.ai |
| `/frontend-design` | Build UI components and pages |
| `/seo-audit` | Full website SEO audit with health score |

---

## Architecture

```
Your Mac (Claude Code)
     │
     ├── Claude Code skills (.claude/skills/)
     ├── LinkedIn posting (linkedin/post_to_linkedin.py)
     ├── YouTube upload (youtube/youtube_upload.py)
     └── Deploy scripts (*/deploy.sh)
              │
              ▼ scp + ssh
         VPS (YOUR_SERVER_IP)
              │
              ├── /var/www/aiexperts/       ← Main website + blog
              ├── /var/www/invoice/         ← Invoice Dashboard  :5001
              ├── /var/www/proposals/       ← Proposal App       :5002
              ├── /var/www/controlcenter/   ← Command Center     :5003
              └── /opt/emailanalyzer/       ← Email Analyzer
```

All Flask apps run as `systemd` services behind Nginx with SSL.

---

## Design System (Main Site)

| Token | Value |
|---|---|
| Background | `#07070e` |
| Accent (gold) | `#c9a96e` |
| Heading font | Cormorant (self-hosted) |
| Body font | Outfit (self-hosted) |

---

## About This Project

This entire business suite was built **live using Claude Code** as course material. Every system — from the invoice app to the full content pipeline — was created through conversation with Claude, with the exact prompts documented in `Original Claude Code Prompts/`.

**Original creator:** Dominik Pascal Felber — [Germanaicreator / Limitless AI Solutions LLC](https://www.youtube.com/@germanaicreator) · [LinkedIn](https://www.linkedin.com/in/dominik-felber-32b71812a/) · [Instagram](https://www.instagram.com/germanaicreator)

See [LICENSE](LICENSE) for terms of use.
