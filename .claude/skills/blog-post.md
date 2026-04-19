---
name: blog-post
description: Create SEO-optimized blog posts for the AI Experts website (AI automation for recruiting agencies) and publish them live. Asks the user for a topic, URL, or raw information, generates the full post with at least one Nano Banana 2 image, and deploys to the server. Use this when the user wants to write, create, publish, or add a blog post.
---

This skill creates a complete, SEO-optimized blog post for the **AI Experts** website (YOUR_DOMAIN) and publishes it live. The business offers custom AI automations for recruiting agencies (CV screening, outreach, ATS automation).

## Business Context

- **Business**: AI Experts — custom AI automations for recruiting agencies
- **Target audience**: Recruiting agency owners, talent acquisition managers, HR tech professionals
- **Value proposition**: Save 30+ hours/week, reduce time-to-hire, automate repetitive tasks, get custom AI in 5 business days
- **Website**: https://YOUR_DOMAIN
- **Server**: YOUR_SERVER_IP, user: root, password in `.env` as `Password`
- **Local web root**: `/Users/dominiks_mac/Business Website Creation/`
- **Server web root**: `/var/www/aiexperts/`
- **Blog index**: `/blog/index.html` (local and on server)
- **Blog posts**: `/blog/posts/{slug}/index.html`
- **Blog images**: `/blog/posts/{slug}/header.jpg`

## Step 1 — Gather Input

Ask the user:
> "What would you like the blog post to be about? You can give me:
> - A topic or idea (e.g., "how AI can speed up CV screening")
> - A URL to an article, resource, or research to base the post on
> - Raw text, notes, or any information you want turned into a post"

If a URL is provided, fetch its content with WebFetch and extract the key information.

## Step 2 — Research & SEO Strategy

Based on the topic and business context, determine:

**Primary keyword** (1): The main search term to rank for. Examples:
- "AI CV screening software"
- "recruiting automation tools"
- "AI for recruiting agencies"
- "automated candidate outreach"
- "AI talent acquisition software"
- "recruiting workflow automation"
- "ATS automation software"
- "AI candidate matching"

**Secondary keywords** (3–5): Supporting terms to weave naturally into the content.

**Search intent**: Informational, commercial, or navigational? Most posts should be informational/educational.

**Title strategy**: Include the primary keyword, be specific, use numbers or power words where natural (e.g., "How AI CV Screening Saves Recruiting Agencies 20+ Hours Per Week").

**Meta description**: 140–160 characters, includes primary keyword, has a clear value proposition.

## Step 3 — Generate the Header Image

Use the **nano-banana-2** skill to create a professional header image for the blog post.

**Image prompt guidelines for this business:**
- Professional, cinematic, high-quality photorealistic style
- Relevant to the topic (AI, technology, recruiting, automation)
- Dark and moody OR clean and modern (match the website's dark aesthetic)
- No faces needed — abstract tech visuals work great
- Examples:
  - "Futuristic AI neural network visualization, dark background with gold and blue energy streams, cinematic lighting, ultra-detailed, 8K quality"
  - "Modern recruiting office with holographic AI interface overlays, dark room with glowing data panels, professional photography, cinematic"
  - "Abstract digital automation pipeline with flowing data nodes in dark space, gold and indigo color palette, photorealistic"
  - "Close-up of CV documents with AI scanning overlay in neon blue, dark dramatic studio lighting, sharp focus, professional"

Save the image to:
- **Local**: `/Users/dominiks_mac/Business Website Creation/blog/posts/{slug}/header.jpg`
- **Aspect ratio**: `16:9`
- **Resolution**: `1K`

Create the post directory first:
```bash
mkdir -p "/Users/dominiks_mac/Business Website Creation/blog/posts/{slug}"
```

## Step 4 — Write the Blog Post Content

Write a comprehensive, SEO-optimized article. Requirements:

**Length**: 1,200–2,000 words (long enough for SEO authority, concise enough to read)

**Structure**:
1. **Introduction** (150–200 words) — Hook with a relatable problem, introduce the primary keyword naturally, preview what the post covers
2. **H2 sections** (3–5 sections, ~200–300 words each) — Each covers a key subtopic, uses secondary keywords naturally
3. **H3 subheadings** within H2s where helpful for scanability
4. **Conclusion + CTA** (100–150 words) — Summary, actionable takeaway, soft CTA to book a free strategy call

**SEO best practices**:
- Primary keyword in H1 (title), first paragraph, at least one H2, and meta description
- Secondary keywords distributed naturally throughout
- Use bullet points and numbered lists for scanability
- Link back to the main website (internal link): `<a href="/">AI Experts</a>` or `<a href="/#services">our services</a>`
- Aim for a Flesch Reading Ease score of 60+ (clear, accessible writing)
- No keyword stuffing — write for humans first

**Tone**: Expert but approachable. Authoritative without being academic. Use "you" and "your agency" to speak directly to the reader.

## Step 5 — Build the HTML File

Create a complete, self-contained HTML page at:
`/Users/dominiks_mac/Business Website Creation/blog/posts/{slug}/index.html`

Use this exact template (fill in all placeholders):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="META_DESCRIPTION_HERE">
  <title>POST_TITLE — AI Experts Blog</title>
  <link rel="icon" type="image/png" href="/favicon.png">
  <link rel="canonical" href="https://YOUR_DOMAIN/blog/posts/SLUG/">
  <meta property="og:type" content="article">
  <meta property="og:title" content="POST_TITLE">
  <meta property="og:description" content="META_DESCRIPTION_HERE">
  <meta property="og:url" content="https://YOUR_DOMAIN/blog/posts/SLUG/">
  <meta property="og:image" content="https://YOUR_DOMAIN/blog/posts/SLUG/header.jpg">
  <meta property="og:site_name" content="AI Experts">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="POST_TITLE">
  <meta name="twitter:description" content="META_DESCRIPTION_HERE">
  <meta name="twitter:image" content="https://YOUR_DOMAIN/blog/posts/SLUG/header.jpg">

  <!-- Article structured data -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "POST_TITLE",
    "description": "META_DESCRIPTION_HERE",
    "image": "https://YOUR_DOMAIN/blog/posts/SLUG/header.jpg",
    "datePublished": "PUBLISH_DATE_ISO",
    "dateModified": "PUBLISH_DATE_ISO",
    "author": {"@type": "Organization", "name": "AI Experts"},
    "publisher": {
      "@type": "Organization",
      "name": "AI Experts",
      "logo": {"@type": "ImageObject", "url": "https://YOUR_DOMAIN/logo_big_white.png"}
    },
    "mainEntityOfPage": {"@type": "WebPage", "@id": "https://YOUR_DOMAIN/blog/posts/SLUG/"}
  }
  </script>

  <link rel="stylesheet" href="/fonts.css">
  <style>
:root{--bg:#07070e;--bg2:#0c0c18;--bg3:#111120;--bgcard:#0f0f1c;--border:rgba(255,255,255,0.07);--bordergold:rgba(201,169,110,0.28);--text:#ede9df;--muted:rgba(237,233,223,0.56);--subtle:rgba(237,233,223,0.32);--gold:#c9a96e;--goldlight:#dfbd84;--golddim:rgba(201,169,110,0.10);--r:12px;--rl:20px;--ease:0.3s cubic-bezier(0.4,0,0.2,1)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'Outfit',sans-serif;font-size:16px;line-height:1.65;overflow-x:hidden;-webkit-font-smoothing:antialiased}
img{max-width:100%;display:block}
a{color:inherit;text-decoration:none}
::selection{background:rgba(201,169,110,0.22);color:var(--text)}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px}
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:999;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");opacity:.4}
h1,h2,h3,h4{font-family:'Cormorant',serif;line-height:1.15}
.container{max-width:1160px;margin:0 auto;padding:0 24px}
.btn{display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:6px;font-family:'Outfit',sans-serif;font-size:.95rem;font-weight:600;cursor:pointer;border:none;transition:var(--ease);text-decoration:none;white-space:nowrap}
.btn-primary{background:var(--gold);color:#07070e}.btn-primary:hover{transform:translateY(-1px);box-shadow:0 8px 32px rgba(201,169,110,.38)}
.btn-ghost{background:transparent;color:var(--text);border:1px solid var(--border)}.btn-ghost:hover{border-color:var(--bordergold);color:var(--gold)}
nav{position:fixed;top:0;left:0;right:0;z-index:100;padding:13px 0;background:rgba(7,7,14,.88);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}
.nav-inner{display:flex;align-items:center;justify-content:space-between;gap:24px}
.nav-logo img{height:34px;width:auto}
.nav-links{display:flex;align-items:center;gap:28px;list-style:none}
.nav-links a{font-size:.88rem;color:var(--muted);transition:color var(--ease)}.nav-links a:hover{color:var(--text)}.nav-links a.active{color:var(--gold)}
.hamburger{display:none;flex-direction:column;gap:5px;cursor:pointer;padding:4px;background:none;border:none}
.hamburger span{display:block;width:22px;height:1.5px;background:var(--text)}
.mob{display:none;position:fixed;inset:0;background:rgba(7,7,14,.97);backdrop-filter:blur(20px);z-index:99;flex-direction:column;align-items:center;justify-content:center;gap:28px}
.mob.open{display:flex}
.mob a{font-family:'Cormorant',serif;font-size:2.4rem;font-weight:500;color:var(--text);transition:color var(--ease)}.mob a:hover{color:var(--gold)}
.mob-close{position:absolute;top:22px;right:22px;background:none;border:1px solid var(--border);color:var(--text);width:38px;height:38px;border-radius:8px;cursor:pointer;font-size:1.1rem;display:flex;align-items:center;justify-content:center}

/* Article layout */
.article-hero{padding:110px 0 0;position:relative;overflow:hidden}
.article-hero-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(201,169,110,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(201,169,110,.03) 1px,transparent 1px);background-size:64px 64px;mask-image:radial-gradient(ellipse 80% 60% at 50% 0%,black 0%,transparent 100%)}
.article-meta-top{position:relative;z-index:2;padding:48px 0 36px}
.breadcrumb{display:flex;align-items:center;gap:8px;font-size:.78rem;color:var(--subtle);margin-bottom:20px}
.breadcrumb a{color:var(--subtle);transition:color var(--ease)}.breadcrumb a:hover{color:var(--gold)}
.breadcrumb span{color:var(--subtle)}
.article-tag{display:inline-block;font-size:.68rem;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);background:var(--golddim);border:1px solid rgba(201,169,110,.2);border-radius:100px;padding:3px 10px;margin-bottom:16px}
.article-title{font-family:'Cormorant',serif;font-size:clamp(2.4rem,4.5vw,4rem);font-weight:600;line-height:1.05;letter-spacing:-.025em;max-width:780px;margin-bottom:20px}
.article-excerpt{font-size:1.08rem;color:var(--muted);line-height:1.72;max-width:640px;margin-bottom:24px}
.article-byline{display:flex;align-items:center;gap:20px;font-size:.82rem;color:var(--subtle);padding-bottom:36px;border-bottom:1px solid var(--border)}
.byline-dot{width:3px;height:3px;border-radius:50%;background:var(--subtle)}

.article-header-img{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:var(--rl);margin-bottom:0;display:block}

.article-body-wrap{display:grid;grid-template-columns:1fr min(720px,100%) 1fr;padding:60px 0 100px}
.article-body-wrap > *{grid-column:2}
.article-content{color:var(--text)}
.article-content p{font-size:1.05rem;line-height:1.8;color:var(--muted);margin-bottom:1.5rem}
.article-content p:first-child{font-size:1.12rem;color:var(--text)}
.article-content h2{font-family:'Cormorant',serif;font-size:clamp(1.7rem,3vw,2.4rem);font-weight:600;color:var(--text);margin:2.8rem 0 1rem;letter-spacing:-.015em}
.article-content h3{font-family:'Cormorant',serif;font-size:clamp(1.3rem,2vw,1.8rem);font-weight:600;color:var(--text);margin:2rem 0 .75rem}
.article-content ul,.article-content ol{margin:0 0 1.5rem 1.5rem;color:var(--muted)}
.article-content li{font-size:1rem;line-height:1.75;margin-bottom:.5rem}
.article-content strong{color:var(--text);font-weight:600}
.article-content a{color:var(--gold);text-decoration:underline;text-underline-offset:3px}
.article-content a:hover{color:var(--goldlight)}
.article-content blockquote{border-left:2px solid var(--gold);padding:16px 20px;margin:2rem 0;background:var(--golddim);border-radius:0 var(--r) var(--r) 0}
.article-content blockquote p{font-family:'Cormorant',serif;font-size:1.2rem;font-style:italic;color:var(--text);margin:0}
.article-content .img-inline{border-radius:var(--r);margin:2rem 0;width:100%;aspect-ratio:16/9;object-fit:cover}
.article-content hr{border:none;border-top:1px solid var(--border);margin:2.5rem 0}

.article-cta{background:var(--bgcard);border:1px solid var(--bordergold);border-radius:var(--rl);padding:36px 40px;margin:3rem 0 0;text-align:center}
.article-cta h3{font-family:'Cormorant',serif;font-size:1.9rem;margin-bottom:12px}
.article-cta h3 em{font-style:italic;color:var(--gold)}
.article-cta p{font-size:.95rem;color:var(--muted);margin-bottom:24px}

.back-link{display:inline-flex;align-items:center;gap:6px;font-size:.85rem;color:var(--muted);margin-top:40px;transition:color var(--ease)}
.back-link:hover{color:var(--gold)}

footer{background:var(--bg2);border-top:1px solid var(--border);padding:60px 0 30px}
.foot-top{display:grid;grid-template-columns:1.6fr 1fr 1fr;gap:60px;margin-bottom:50px}
.foot-brand p{font-size:.9rem;color:var(--muted);line-height:1.7;margin-top:16px;max-width:300px}
.foot-brand img{height:30px;width:auto}
.foot-col h4{font-family:'Cormorant',serif;font-size:1.1rem;font-weight:600;margin-bottom:16px;color:var(--text)}
.foot-links{list-style:none;display:flex;flex-direction:column;gap:10px}
.foot-links a{font-size:.88rem;color:var(--muted);transition:color var(--ease)}.foot-links a:hover{color:var(--gold)}
.foot-social{display:flex;gap:10px;margin-top:20px}
.soc{width:34px;height:34px;border:1px solid var(--border);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--muted);transition:var(--ease)}.soc:hover{border-color:var(--bordergold);color:var(--gold)}
.foot-btm{display:flex;align-items:center;justify-content:space-between;padding-top:24px;border-top:1px solid var(--border)}
.foot-copy{font-size:.82rem;color:var(--subtle)}
.foot-legal{display:flex;gap:20px}.foot-legal a{font-size:.82rem;color:var(--subtle);transition:color var(--ease)}.foot-legal a:hover{color:var(--muted)}

@media(max-width:768px){
  .nav-links,.nav-cta{display:none}.hamburger{display:flex}
  .article-body-wrap{grid-template-columns:0 1fr 0;padding:40px 0 80px}
  .article-body-wrap > *{grid-column:2;padding:0 20px}
  .foot-top{grid-template-columns:1fr}.foot-btm{flex-direction:column;gap:16px;text-align:center}
  .article-cta{padding:24px}
}
  </style>
</head>
<body>

<nav>
  <div class="container">
    <div class="nav-inner">
      <a href="/" class="nav-logo"><picture><source srcset="/logo_big_white.webp" type="image/webp"><img src="/logo_big_white.png" alt="AI Experts" height="34"></picture></a>
      <ul class="nav-links">
        <li><a href="/#problem">Problem</a></li>
        <li><a href="/#services">Services</a></li>
        <li><a href="/#results">Results</a></li>
        <li><a href="/#process">Process</a></li>
        <li><a href="/#about">About</a></li>
        <li><a href="/#faq">FAQ</a></li>
        <li><a href="/blog/" class="active">Blog</a></li>
      </ul>
      <div class="nav-cta">
        <a href="" class="btn btn-ghost" onclick="if(window.Calendly){Calendly.initPopupWidget({url:'https://calendly.com/dominik-limitless-ai-solutions/30min'});}else{window.open('https://calendly.com/dominik-limitless-ai-solutions/30min','_blank');}return false;">Book a Call</a>
      </div>
      <button class="hamburger" id="ham" aria-label="Menu"><span></span><span></span><span></span></button>
    </div>
  </div>
</nav>

<div class="mob" id="mob">
  <button class="mob-close" id="mob-close">&#x2715;</button>
  <a href="/#problem">Problem</a>
  <a href="/#services">Services</a>
  <a href="/#results">Results</a>
  <a href="/#about">About</a>
  <a href="/blog/" style="color:var(--gold)">Blog</a>
  <a href="" class="btn btn-primary" style="margin-top:12px" onclick="if(window.Calendly){Calendly.initPopupWidget({url:'https://calendly.com/dominik-limitless-ai-solutions/30min'});}else{window.open('https://calendly.com/dominik-limitless-ai-solutions/30min','_blank');}return false;">Book a Free Strategy Call</a>
</div>

<div class="article-hero">
  <div class="article-hero-grid"></div>
  <div class="container">
    <div class="article-meta-top">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a><span>›</span><a href="/blog/">Blog</a><span>›</span><span>CATEGORY_HERE</span>
      </nav>
      <span class="article-tag">CATEGORY_HERE</span>
      <h1 class="article-title">POST_TITLE_HERE</h1>
      <p class="article-excerpt">EXCERPT_HERE</p>
      <div class="article-byline">
        <span>AI Experts</span>
        <span class="byline-dot"></span>
        <time datetime="PUBLISH_DATE_ISO">PUBLISH_DATE_HUMAN</time>
        <span class="byline-dot"></span>
        <span>READ_TIME min read</span>
      </div>
    </div>
  </div>
  <div class="container" style="padding-bottom:0">
    <img src="header.jpg" alt="POST_TITLE_HERE" class="article-header-img" loading="eager">
  </div>
</div>

<div class="article-body-wrap">
  <article class="article-content">

    <!-- ARTICLE_CONTENT_HERE -->

    <div class="article-cta">
      <h3>Ready to <em>automate</em> your recruiting workflow?</h3>
      <p>Book a free 30-minute strategy call. We'll map out exactly which parts of your workflow can be automated and what results you can expect.</p>
      <a href="" class="btn btn-primary" onclick="if(window.Calendly){Calendly.initPopupWidget({url:'https://calendly.com/dominik-limitless-ai-solutions/30min'});}else{window.open('https://calendly.com/dominik-limitless-ai-solutions/30min','_blank');}return false;">Book Your Free Strategy Call →</a>
    </div>

    <a href="/blog/" class="back-link">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
      Back to all articles
    </a>
  </article>
</div>

<footer>
  <div class="container">
    <div class="foot-top">
      <div class="foot-brand">
        <picture><source srcset="/logo_big_white.webp" type="image/webp"><img src="/logo_big_white.png" alt="AI Experts" height="30" loading="lazy"></picture>
        <p>Custom AI automations for recruiting agencies. CV screening, personalised outreach, candidate follow-ups, ATS automation — delivered in 5 business days.</p>
        <div class="foot-social">
          <a href="https://www.linkedin.com/company/limitless-ai-solutions-llc" target="_blank" rel="noopener noreferrer" class="soc" aria-label="LinkedIn"><svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z"/><circle cx="4" cy="4" r="2"/></svg></a>
          <a href="https://www.instagram.com/germanaicreator" target="_blank" rel="noopener noreferrer" class="soc" aria-label="Instagram"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5"/><path d="M16 11.37A4 4 0 1112.63 8 4 4 0 0116 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a>
        </div>
      </div>
      <div class="foot-col">
        <h4>Navigation</h4>
        <ul class="foot-links">
          <li><a href="/#problem">The Problem</a></li>
          <li><a href="/#services">Services</a></li>
          <li><a href="/#results">Client Results</a></li>
          <li><a href="/#about">About</a></li>
          <li><a href="/blog/">Blog</a></li>
        </ul>
      </div>
      <div class="foot-col">
        <h4>Contact</h4>
        <ul class="foot-links">
          <li><a href="mailto:YOUR_EMAIL">YOUR_EMAIL</a></li>
          <li><a href="" onclick="if(window.Calendly){Calendly.initPopupWidget({url:'https://calendly.com/dominik-limitless-ai-solutions/30min'});}else{window.open('https://calendly.com/dominik-limitless-ai-solutions/30min','_blank');}return false;">Book a Strategy Call</a></li>
          <li><a href="https://www.linkedin.com/company/limitless-ai-solutions-llc" target="_blank" rel="noopener noreferrer">LinkedIn</a></li>
        </ul>
      </div>
    </div>
    <div class="foot-btm">
      <p class="foot-copy">© 2026 AI Experts. All rights reserved.</p>
      <div class="foot-legal"><a href="/imprint/">Imprint</a><a href="/privacy/">Privacy Policy</a></div>
    </div>
  </div>
</footer>

<script>
const ham=document.getElementById('ham'),mob=document.getElementById('mob'),mc=document.getElementById('mob-close');
if(ham&&mob){ham.addEventListener('click',()=>mob.classList.add('open'));mc.addEventListener('click',()=>mob.classList.remove('open'));mob.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>mob.classList.remove('open')));}
</script>
</body>
</html>
```

## Step 6 — Update the Blog Index Page

After writing the post HTML, update the blog index at:
`/Users/dominiks_mac/Business Website Creation/blog/index.html`

Find the comment markers `<!-- POSTS_START -->` and `<!-- POSTS_END -->` and replace the content between them with updated post cards (prepend the new post card so newest is first).

**Post card HTML template** (add one per post, newest first):
```html
      <article class="post-card rv FEATURED_OR_EMPTY d1">
        <a href="/blog/posts/SLUG/" class="post-card-img">
          <img src="/blog/posts/SLUG/header.jpg" alt="POST_TITLE" loading="lazy">
        </a>
        <div class="post-card-body">
          <span class="post-tag">CATEGORY</span>
          <h2><a href="/blog/posts/SLUG/">POST_TITLE</a></h2>
          <p>EXCERPT (2-3 sentences)</p>
          <div class="post-meta">
            <time datetime="ISO_DATE">HUMAN_DATE</time>
            <span class="post-meta-dot"></span>
            <span>READ_TIME min read</span>
          </div>
          <a href="/blog/posts/SLUG/" class="post-read-more">Read article <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></a>
        </div>
      </article>
```

For the **first/featured post**, add class `featured` to the article element:
```html
      <article class="post-card featured rv d1">
```

If there are multiple posts, the first one gets `featured`, the rest are regular cards.

## Step 7 — Deploy to Server

Upload all new/changed files to the server using sshpass + scp:

**Deploy new post directory:**
```bash
# Create directory on server
sshpass -p 'SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@YOUR_SERVER_IP "mkdir -p /var/www/aiexperts/blog/posts/SLUG"

# Upload post HTML
sshpass -p 'SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  "/Users/dominiks_mac/Business Website Creation/blog/posts/SLUG/index.html" \
  root@YOUR_SERVER_IP:/var/www/aiexperts/blog/posts/SLUG/index.html

# Upload header image
sshpass -p 'SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  "/Users/dominiks_mac/Business Website Creation/blog/posts/SLUG/header.jpg" \
  root@YOUR_SERVER_IP:/var/www/aiexperts/blog/posts/SLUG/header.jpg

# Upload updated blog index
sshpass -p 'SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  "/Users/dominiks_mac/Business Website Creation/blog/index.html" \
  root@YOUR_SERVER_IP:/var/www/aiexperts/blog/index.html
```

Read the server password from `.env` (the `Password` field).

## Step 8 — Confirm and Report

After deployment, report to the user:
- Live URL: `https://YOUR_DOMAIN/blog/posts/SLUG/`
- Blog index: `https://YOUR_DOMAIN/blog/`
- SEO target keyword
- Word count
- Confirm image was generated and uploaded

## Slug Generation Rules

- Lowercase only
- Words separated by hyphens
- No special characters
- Max 6 words
- Include primary keyword
- Examples: `ai-cv-screening-recruiting-agencies`, `automated-candidate-outreach-guide`, `ats-automation-recruiting`

## Read Time Calculation

Approximate: `ceil(word_count / 200)` minutes

## Category Options

Choose the most relevant:
- `AI Automation`
- `Recruiting Tech`
- `Productivity`
- `Case Study`
- `How-To Guide`
- `Industry Trends`

## Important Notes

- Always read the existing `blog/index.html` before editing it (use Read tool) to preserve existing post cards
- The `POSTS_START` / `POSTS_END` comments are the injection points — preserve them
- Test that all file paths are correct before uploading
- The server password is the `Password` field in `.env`, not `KeyAI_API_KEY`
- Always verify the image file was successfully saved before uploading (check file exists and size > 0)
- If image generation fails, generate the post without the image and note this to the user
