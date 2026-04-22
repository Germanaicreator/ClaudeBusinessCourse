# Web & VPS Security Audit Skill

## Purpose
Analyze the security posture of websites, web applications, and their underlying server infrastructure. Produce a structured vulnerability report with severity ratings and actionable remediation steps. The target is **industry-standard security for 2026** — thorough but not paranoid.

---

## When to Use This Skill
Trigger this skill when a user asks to:
- Audit the security of a VPS, web server, or web application
- Review SSH, firewall, Nginx, or database configuration files
- Check for known vulnerabilities in Python/Node/PHP dependencies
- Generate a security report or hardening checklist
- Assess compliance with modern security baselines (OWASP, CIS, Mozilla)

---

## Audit Scope & Checklist

Work through each domain below. For each item, determine: **PASS / FAIL / WARN / N/A**, note evidence, and assign a severity if it fails.

### Severity Scale
| Level | Meaning |
|---|---|
| CRITICAL | Actively exploitable; fix immediately |
| HIGH | Likely to be exploited; fix within 48 hours |
| MEDIUM | Should be fixed in the next sprint/release |
| LOW | Best-practice gap; fix when convenient |
| INFO | Informational observation, no action required |

---

## Domain 1: Server Infrastructure (OS & Access)

### 1.1 SSH Authentication
**Check:**
grep -E "^PasswordAuthentication|^PubkeyAuthentication|^PermitRootLogin|^MaxAuthTries|^LoginGraceTime|^Port" /etc/ssh/sshd_config

**Pass conditions:**
- PasswordAuthentication no
- PubkeyAuthentication yes
- PermitRootLogin no
- MaxAuthTries 3 or lower
- LoginGraceTime 30 or lower
- Port is NOT 22 (ideally 49152-65535)
- SSH keys are Ed25519, not RSA-1024/2048

**Fail guidance:**
- CRITICAL: Password login enabled -> immediate brute-force risk
- CRITICAL: Root login permitted -> full system takeover if credentials leak
- MEDIUM: Default port 22 -> high automated scanning noise
- MEDIUM: RSA key < 4096 bits -> consider migrating to Ed25519

### 1.2 Automatic Security Updates
**Check:**
dpkg -l unattended-upgrades 2>/dev/null || rpm -q dnf-automatic 2>/dev/null

**Pass conditions:**
- unattended-upgrades (Debian/Ubuntu) or dnf-automatic (RHEL/Fedora) installed and enabled
- Security-only updates configured to apply daily
- Reboot-required notifications in place

**Fail guidance:**
- HIGH: Not installed -> known CVEs may go unpatched for weeks

### 1.3 Intrusion Prevention (Fail2Ban)
**Check:**
systemctl status fail2ban && fail2ban-client status sshd

**Pass conditions:**
- Fail2Ban active and running
- sshd jail enabled
- maxretry <= 5, bantime >= 3600

**Fail guidance:**
- HIGH: Not running -> brute-force attempts proceed unimpeded

### 1.4 OS Hardening Extras
**Check:**
sysctl kernel.randomize_va_space   # Should be 2
sysctl net.ipv4.tcp_syncookies     # Should be 1
awk -F: '($3 == 0) { print $1 }' /etc/passwd   # Should only be root

**Pass conditions:**
- ASLR enabled (kernel.randomize_va_space = 2)
- SYN cookies enabled
- No unexpected UID-0 accounts

---

## Domain 2: Network & Firewall

### 2.1 Firewall Policy
**Check:**
ufw status verbose

**Pass conditions:**
- Default policy is DENY (incoming and forwarded)
- Only ports 80, 443, and custom SSH port are open to public
- All other ports blocked or limited to specific source IPs

**Fail guidance:**
- CRITICAL: Default ALLOW policy -> entire server surface exposed
- HIGH: Database ports (5432, 3306, 6379) open to public

### 2.2 Private Networking / VPC
**Check:**
ss -tlnp | grep -E "5432|3306|6379|27017"

**Pass conditions:**
- Database services bind to 127.0.0.1 or a private IP only
- Multi-server setups use private LAN/VPC for inter-service traffic

**Fail guidance:**
- CRITICAL: DB port exposed on 0.0.0.0 -> direct remote database access possible

### 2.3 Port Scan (External Perspective)
**Check (run externally or via online tool):**
nmap -sV -p 1-65535 --open your.server.ip

**Pass conditions:**
- Only expected ports appear open
- No forgotten dev/admin services (8080, 8443, 3000, 9200/Elasticsearch, etc.)

**Fail guidance:**
- HIGH: Unexpected open ports -> attack surface wider than intended

---

## Domain 3: Web Server & TLS (Nginx / Apache)

### 3.1 TLS Configuration
**Check:**
curl -sI https://yourdomain.com | grep -i "strict-transport"
External: https://www.ssllabs.com/ssltest/ and https://ssl-config.mozilla.org/

**Pass conditions:**
- TLS 1.0 and 1.1 disabled; only TLS 1.2 and 1.3 active
- Cipher suites follow Mozilla Intermediate or Modern profile
- Certificate valid (Let's Encrypt / ZeroSSL acceptable)
- SSL Labs score: A or A+

**Fail guidance:**
- CRITICAL: TLS 1.0/1.1 enabled -> POODLE, BEAST attack surface
- HIGH: Weak ciphers (RC4, 3DES, NULL) -> decryption attacks possible

### 3.2 HSTS
**Check:**
curl -sI https://yourdomain.com | grep -i "strict-transport-security"

**Pass conditions:**
- Header present: Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
- max-age >= 1 year (31536000 seconds)

**Fail guidance:**
- MEDIUM: Missing HSTS -> browsers may silently downgrade to HTTP

### 3.3 Security Headers
**Check:**
curl -sI https://yourdomain.com
External grade: https://securityheaders.com

Required headers:
- Content-Security-Policy (HIGH if missing)
- X-Frame-Options: DENY (MEDIUM if missing)
- X-Content-Type-Options: nosniff (MEDIUM if missing)
- Referrer-Policy: strict-origin-when-cross-origin (LOW if missing)
- Permissions-Policy: disable unused APIs (LOW if missing)
- Cross-Origin-Opener-Policy: same-origin (LOW if missing)
- Cross-Origin-Resource-Policy: same-origin (LOW if missing)

CSP Starter Template:
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests;

### 3.4 Rate Limiting
**Check:**
grep -r "limit_req" /etc/nginx/

**Pass conditions:**
- limit_req_zone defined for login endpoints and APIs
- Return 429 Too Many Requests on breach

**Fail guidance:**
- HIGH: No rate limiting on /login, /api/* -> credential stuffing and scraping

### 3.5 Information Leakage
**Check:**
curl -sI https://yourdomain.com | grep -iE "server:|x-powered-by:"

**Pass conditions:**
- Server: header removed (server_tokens off; in Nginx)
- No X-Powered-By version header leaked
- No stack traces visible in error pages

**Fail guidance:**
- LOW: Version disclosure -> attacker knows exactly which CVEs to target

---

## Domain 4: Python Application Security

### 4.1 Dependency Vulnerabilities
**Check:**
pip-audit -r requirements.txt

**Pass conditions:**
- Zero known CVEs in dependencies
- pip-audit run in CI/CD pipeline on every deploy

**Fail guidance:**
- CRITICAL: RCE CVE in dependency -> patch immediately
- HIGH: High severity CVE -> patch within 48 hours

### 4.2 Secret Management
**Check:**
grep -rE "(SECRET_KEY|API_KEY|DB_PASSWORD|PRIVATE_KEY)\s*=" ./app --include="*.py"
trufflehog git file://. --no-update 2>/dev/null

**Pass conditions:**
- No secrets hardcoded in source files
- .env exists and is in .gitignore
- Secrets loaded via python-dotenv, environment variables, or a vault

**Fail guidance:**
- CRITICAL: Hardcoded credentials -> rotate all affected secrets immediately

### 4.3 Debug Mode & Production Flags
**Check:**
grep -rE "DEBUG\s*=\s*True" ./app --include="*.py"

**Pass conditions:**
- DEBUG = False in production configuration
- Set via environment variable, not hardcoded
- Django: ALLOWED_HOSTS not set to ['*']

**Fail guidance:**
- CRITICAL: DEBUG = True in production -> stack traces and internal paths exposed

### 4.4 Process Isolation & Least Privilege
**Check:**
ps aux | grep -E "gunicorn|uvicorn|uwsgi|flask"

**Pass conditions:**
- App runs as a dedicated non-root user (e.g., appuser, www-data)
- App user has no sudo rights
- Virtual environment used (.venv/, venv/) -- not system Python

**Fail guidance:**
- CRITICAL: App running as root -> full server compromise via app vulnerability

### 4.5 SQL Injection Prevention
**Check (code review):**
Look for patterns like: cursor.execute("SELECT ... WHERE id=" + user_input)

**Pass conditions:**
- All DB queries use ORM or parameterized queries
- No string concatenation or f-strings used to build SQL

**Fail guidance:**
- CRITICAL: Raw SQL with user input -> full data exfiltration via SQLi

### 4.6 Authentication & Session Security
**Check:**
curl -sI https://yourdomain.com/login -c /tmp/cookies.txt && cat /tmp/cookies.txt

**Pass conditions:**
- Session cookies have HttpOnly, Secure, and SameSite=Lax (or Strict) flags
- Passwords hashed with bcrypt, argon2, or scrypt (NOT MD5 or SHA1)
- CSRF protection enabled (Django CSRF middleware, Flask-WTF)
- MFA available for admin accounts

**Fail guidance:**
- CRITICAL: MD5/plaintext passwords -> entire user database compromised if leaked
- HIGH: Missing HttpOnly cookie flag -> XSS can steal session tokens

---

## Domain 5: Database Hardening

### 5.1 Network Binding
**Check:**
grep -E "^listen_addresses" /etc/postgresql/*/main/postgresql.conf
grep -E "^bind-address" /etc/mysql/my.cnf
grep -E "^bind" /etc/redis/redis.conf

**Pass conditions:**
- PostgreSQL: listen_addresses = 'localhost' or private IP only
- MySQL: bind-address = 127.0.0.1
- Redis: bind 127.0.0.1 and protected-mode yes

**Fail guidance:**
- CRITICAL: Database bound to 0.0.0.0 with weak/no auth

### 5.2 Authentication Strength
**Check (PostgreSQL):**
grep -E "^host" /etc/postgresql/*/main/pg_hba.conf

**Pass conditions:**
- Authentication method is scram-sha-256, not md5 or trust
- No trust entries for non-local connections
- MySQL: validate_password plugin enabled

**Fail guidance:**
- HIGH: MD5 auth -> offline hash cracking possible
- CRITICAL: trust auth -> no password required at all

### 5.3 Least Privilege DB User
**Check:**
psql -c "\du"

**Pass conditions:**
- App connects with only SELECT, INSERT, UPDATE, DELETE on its own database
- No SUPERUSER, CREATEROLE, or CREATEDB privileges
- Separate users for read-only vs read-write access

**Fail guidance:**
- HIGH: App uses superuser -> SQLi has full database access

### 5.4 Encryption at Rest
**Check:**
- Verify full-disk encryption (LUKS) or tablespace encryption for sensitive data
- Verify database backups are encrypted before off-site transfer

**Fail guidance:**
- MEDIUM: Unencrypted backups -> data exposed if backup storage is compromised

---

## Domain 6: Modern 2026 Standards

### 6.1 Software Bill of Materials (SBOM)
**Check:**
pip-audit --format cyclonedx-json -o sbom.json
syft . -o cyclonedx-json > sbom.json

**Pass conditions:**
- SBOM generated in CycloneDX or SPDX format alongside each release
- SBOM re-generated on every dependency update
- Process enables CVE triage in < 1 hour for Log4j-style events

**Fail guidance:**
- LOW: No SBOM -> can't rapidly assess blast radius of a new zero-day

### 6.2 AI Bot & Scraper Protection
**Check:**
curl https://yourdomain.com/robots.txt

**Pass conditions:**
- robots.txt disallows known aggressive bots (GPTBot, CCBot, Bytespider, etc.)
- Nginx rate limiting applied globally, not just on login endpoints
- Optional: Cloudflare Bot Management or WAF

**Fail guidance:**
- LOW: No bot controls -> aggressive scrapers can cause unintentional DoS on small VPS

### 6.3 Centralized & Off-Site Logging
**Check:**
systemctl status logcheck rsyslog filebeat 2>/dev/null

**Pass conditions:**
- Logs shipped off-server (Loki, Elasticsearch, Cloudwatch, Logtail, Papertrail, etc.)
- auth.log and Nginx logs retained >= 90 days
- Alerts for: root login, new sudo usage, repeated auth failures

**Fail guidance:**
- HIGH: Logs only on-server -> attacker wipes them; no forensics possible post-breach

### 6.4 Backup Strategy (3-2-1 Rule)
**Check:**
crontab -l | grep backup && ls -lh /var/backups/

**Pass conditions:**
- 3 copies of data exist
- 2 different storage media (local disk + cloud object storage)
- 1 copy is off-site (separate cloud region or provider)
- Backups are encrypted before transfer
- Restoration tested at least once every 6 months

**Fail guidance:**
- CRITICAL: No off-site backup -> ransomware or hardware failure = total data loss
- HIGH: Untested backups -> restoration may silently fail when needed most

### 6.5 Web Application Firewall (WAF)
**Check:**
- Is Cloudflare, AWS WAF, ModSecurity, or equivalent active?
- Are OWASP Core Rule Set rules enabled?

**Pass conditions:**
- WAF in front of origin (Cloudflare free tier is sufficient for most sites)
- Blocks SQLi, XSS, and path traversal attempts at edge
- Origin IP not publicly discoverable (Cloudflare Authenticated Origin Pulls)

**Fail guidance:**
- MEDIUM: No WAF -> application-layer attacks hit origin directly

### 6.6 Secrets Scanning in CI/CD
**Check:**
cat .pre-commit-config.yaml 2>/dev/null | grep -E "detect-secrets|gitleaks|trufflehog"
cat .github/workflows/*.yml 2>/dev/null | grep -E "gitleaks|detect-secrets"

**Pass conditions:**
- gitleaks or detect-secrets runs as a pre-commit hook or CI check
- GitHub/GitLab secret scanning enabled on the repository

**Fail guidance:**
- HIGH: No secrets scanning -> credentials regularly committed without detection

---

## Output: Security Audit Report Template

After running all checks, produce the following report:

---
# Security Audit Report
**Target:** [domain / server IP]
**Date:** [YYYY-MM-DD]
**Auditor:** Claude Security Audit Skill v1.0
**Overall Grade:** [A / B / C / D / F]

## Executive Summary
[2-4 sentences: what was audited, the most critical finding, and overall posture]

## Findings

### CRITICAL
| # | Area | Finding | Evidence | Remediation |
|---|---|---|---|---|
| C-01 | SSH | Password auth enabled | PasswordAuthentication yes | Set PasswordAuthentication no, restart sshd |

### HIGH
| # | Area | Finding | Evidence | Remediation |
|---|---|---|---|---|

### MEDIUM
| # | Area | Finding | Evidence | Remediation |
|---|---|---|---|---|

### LOW / INFO
| # | Area | Finding | Evidence | Remediation |
|---|---|---|---|---|

## Passed Checks
- TLS 1.0/1.1 disabled
- Fail2Ban active with sshd jail
- [add all passing items]

## Remediation Priority Queue
1. [Most critical fix - one sentence]
2. [Second most critical]
3. [Continue...]

## Next Audit Recommended
[3-6 months from now, or after any major infrastructure change]
---

---

## Quick Reference: Full Audit Command Sequence

```bash
# 1. SSH config
grep -E "^PasswordAuthentication|^PermitRootLogin|^Port|^MaxAuthTries|^LoginGraceTime" /etc/ssh/sshd_config

# 2. Firewall
ufw status verbose

# 3. All listening ports
ss -tlnp

# 4. HTTP response headers
curl -sI https://yourdomain.com

# 5. TLS quality -- visit: https://www.ssllabs.com/ssltest/

# 6. Security headers -- visit: https://securityheaders.com

# 7. Python dependency CVEs
pip-audit -r requirements.txt

# 8. Secrets in source code
grep -rE "(SECRET_KEY|API_KEY|PASSWORD)\s*=" ./app --include="*.py"

# 9. Database binding
ss -tlnp | grep -E "5432|3306|6379"

# 10. App process ownership
ps aux | grep -E "gunicorn|uvicorn|uwsgi"

# 11. Fail2Ban status
fail2ban-client status sshd

# 12. Backups
ls -lh /var/backups/ && crontab -l | grep backup
```

---

## External Tools & References

| Tool | Purpose | URL |
|---|---|---|
| SSL Labs | TLS/certificate analysis | https://www.ssllabs.com/ssltest/ |
| Security Headers | HTTP header grader | https://securityheaders.com |
| Mozilla SSL Config | Nginx/Apache TLS templates | https://ssl-config.mozilla.org |
| Shodan | External port scan view | https://www.shodan.io |
| pip-audit | Python CVE scanner | pip install pip-audit |
| Gitleaks | Secrets in git history | https://github.com/gitleaks/gitleaks |
| Syft | SBOM generator | https://github.com/anchore/syft |
| OWASP Top 10 | Web app risk reference | https://owasp.org/Top10/ |
| CIS Benchmarks | OS hardening baselines | https://www.cisecurity.org/cis-benchmarks |
| OWASP ZAP | Dynamic application security testing | https://www.zaproxy.org |

---

## Scope Limitations

This skill covers infrastructure and configuration security. It does not replace:
- Manual penetration testing for business logic flaws
- Full DAST scanning (use OWASP ZAP or Burp Suite for that)
- Compliance audits (SOC 2, ISO 27001, GDPR) which require human review
- Deep code-level security review beyond the pattern checks listed above

For production systems handling sensitive PII or financial data, supplement this audit with a professional pentest at least annually.
