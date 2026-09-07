# HamroNepal.com — Project Report

*As of 2026-09-07. This is a snapshot of what actually exists in the codebase today, verified against the code itself rather than copied from other docs — some of which (`ROADMAP.md`, `README.md`) are now out of date in a few details (e.g. they still say Django 6.1 and locale code `ne`; both changed since those were written). This report supersedes them for "what's actually built" purposes.*

## What HamroNepal is

A "Process OS" for Nepal: instead of an article explaining how to register a company or renew a passport, HamroNepal turns each government process into a structured, source-cited, trackable checklist — real steps, real fees, an official source with a verification date, and progress tracking from start to finish. A second section, `/tourism`, does the same discovery-to-planning job for travel: real destinations, categories, seasonal guidance, and a personal trip planner. The whole site explicitly is **not** a government office — every process links back to the real official source as the final authority.

## At a glance

| | |
|---|---|
| Backend | Django 5.1.15, PostgreSQL, Redis (prod falls back to local-memory cache — no Redis on the current host) |
| Frontend | Django templates + HTMX + Tailwind CSS v4 (standalone CLI, no Node/npm) |
| Languages | English + Nepali (locale code `np`), 422 translated UI strings |
| Apps | `core`, `accounts`, `locations`, `organizations`, `processes`, `tasks`, `dashboard`, `tourism` |
| Automated tests | 239, all passing |
| Hosting | cPanel shared hosting, Phusion Passenger (WSGI), WhiteNoise for static files |
| Real seeded content | 3 government processes, 6 tourism destinations, 7 provinces / 77 districts / 1 municipality (Kathmandu Metro only — see Known Gaps) |

## 1. Foundation (built before this session)

Documented in detail, phase-by-phase, in `ROADMAP.md`. Summary of what's there:

- **Data model**: custom email-based `User` + `Profile`; `Province → District → Municipality → Ward`; `GovernmentOrganization`/`GovernmentOffice`; the full Process Engine schema (`Process`, `ProcessStep`, `ProcessRequirement`, `ProcessSource`, `ProcessFAQ`, `ProcessVersion`, per-user progress tracking); `Task`/`Reminder`.
- **Admin CMS**: staff can create/edit processes with inline steps, requirements, sources, and FAQs. A process cannot be published without at least one cited source (`services.publish_new_version` refuses it) — enforced in code, not policy. Publishing snapshots the full process into a versioned `ProcessVersion` record.
- **Auth**: register, email verification, login, password reset, profile editing — rate-limited on every unauthenticated write endpoint.
- **Design system**: Tailwind v4 (CSS-first `@theme` tokens), a shared `base.html` shell, navbar/footer, reusable component library (`components/ui/`, `components/dashboard/`, icon set).
- **Homepage & search**: intent-driven search box, Postgres full-text search (English stemmed, Nepali tokenized — Postgres has no Nepali linguistic config, so this is an honest limitation, not hidden).
- **Process Engine**: full detail page (steps, requirements, fees, sources, FAQs, `HowTo`/`FAQPage` JSON-LD), individual/business variant paths, step-by-step tracking with status milestones (not started → preparing → applied → processing → completed).
- **Dashboard**: active processes with progress bars, personal task list.
- **Content seeding**: 3 real, fact-checked processes (company registration, PAN registration, passport application), each researched from the primary government source directly, not secondhand — including one documented case where third-party blogs had the passport fee wrong and the seeded content used the government's own figure instead, with the discrepancy disclosed in a FAQ.
- **i18n**: full English/Nepali coverage of UI chrome and seeded content, with fallback so an untranslated field shows English rather than blank.
- **Testing/SEO**: the original 71-test suite (since grown), `sitemap.xml`, `robots.txt`, custom error pages, `manage.py check --deploy` clean.

## 2. Built this session

### Profile/settings page redesign
Restyled to match the glass-card treatment already used on login/register — no functional changes.

### `/tourism` — a full second product surface
A premium, editorially-designed destination-discovery and trip-planning platform, visually distinct from the dashboard while sharing the brand (Nepal's actual geography and culture, not the cliché mountains/flags/prayer-flags treatment).

- **Models**: `DestinationCategory`, `Destination`, `DestinationHighlight`, `SavedPlace`, `RecentlyViewedDestination`, `Trip`, `TripDestination`.
- **Content**: 6 real, fact-verified flagship destinations (Kathmandu Valley, Pokhara, Chitwan National Park, Everest/Khumbu, Lumbini, Rara Lake) across 5 experience categories, each cited to a real source (Wikipedia, since UNESCO's own site blocked direct verification) with a verification date — same rigor as the process content.
- **Imagery**: real `ImageField` slots exist on `Destination` for real photography later; v1 ships with no photos and a non-photographic editorial treatment (category-tinted gradients, typography) rather than fabricated stock imagery.
- **Frontend**: an asymmetric bento-grid landing page, horizontal category carousel, seasonal recommendations derived from the real current month (not invented "editor's picks"), destination detail pages with JSON-LD, and an HTMX-driven trip itinerary builder (add/remove destinations, with a fixed bug where the "available destinations" picker used to go stale after an add).
- **Access**: public browsing/search; save/bookmark and trip planning require an account, fully ownership-isolated (a second user can't see, add to, or delete another user's trip — tested).
- Registered in the sitemap, linked from the navbar ("Explore Nepal"), fully bilingual, own test suite (models/services/views/ownership/smoke test).

### "Try all features for free" banner
A slim promotional bar above the navbar, shown to anonymous visitors only, linking to registration.

### Deploy strategy fix: compiled CSS now committed to git
The production host's `/tmp` is mounted `noexec`, which broke the Bun-based standalone `tailwindcss` binary at build time (`ERR_DLOPEN_FAILED`). Rather than fight the host's filesystem restrictions, `theme/static/css/dist/styles.css` is now built locally and committed directly — the server no longer needs to run a Tailwind build at all, just `collectstatic`.

### Legal & compliance
- Real **Privacy Policy**, **Terms and Conditions**, **Cookie Policy**, and **Refund Policy** pages at `/privacy/`, `/terms/`, `/cookies/`, `/refunds/`, written against what the site actually does (audited first: no analytics, no third-party trackers, no payment processing) rather than generic boilerplate.
- Registration now requires an explicit "I agree to the Terms and Privacy Policy" checkbox, with a `terms_accepted_at` timestamp saved as real evidence of consent.
- No cookie-consent banner — the site only sets strictly-necessary cookies (session, CSRF, language), which don't require opt-in consent under GDPR/ePrivacy; the Cookie Policy discloses them by name instead.
- Accessibility fixes: two content-bearing images had meaningless empty `alt` text (now fixed), and a real WCAG failure where a dashboard nav link's only accessible name was hidden via `display:none` whenever the sidebar was collapsed (fixed).
- A translation-extraction bug was found and fixed along the way: an escaped straight quote inside a `{% translate %}` tag argument was silently truncating that sentence during `makemessages` — would have shipped a broken Nepali translation.
- **Open item, disclosed on the page itself**: the Privacy Policy currently names the operator as unconfirmed (an amber warning box on the page) — real legal protection needs a real business/entity name filled in.

### Security hardening
- **Content-Security-Policy** (via `django-csp`): strict `script-src` with per-request nonces, no `unsafe-eval`/`unsafe-inline` for scripts. The last 3 raw `onclick`/`onchange`/`onsubmit` attributes anywhere in the codebase were converted to proper `addEventListener` JS, and htmx's `allowEval` (a feature never used here) was explicitly disabled so htmx stops even attempting it. Verified with a live browser sweep across every page plus a real htmx AJAX interaction — zero real CSP violations.
- **File upload limits**: avatars, dashboard documents, and destination images previously had no server-side size cap (only a valid-image check) — added a real 5MB limit on all three.
- **Admin login rate-limited**: Django's built-in `/admin/login/` had no brute-force protection, unlike every other auth entry point — now matches the same 10/min-per-IP limit.
- **Admin permissions tightened**: `UserDocument` (private uploads — passport/citizenship scans etc.) is now restricted to superusers in the admin, rather than any staff account with the model permission.
- **Confirmed clean by audit, no changes needed**: no secrets in git history or hardcoded anywhere (all via env vars), no raw SQL, no unsafe `|safe`/`mark_safe` beyond one already-correct JSON-LD case, no `csrf_exempt` anywhere, every user-owned object fetch in every view scoped to `request.user`, file-upload path traversal confirmed blocked by Django's storage layer, HTTPS/HSTS/secure-cookies already correctly set. `manage.py check --deploy` against real production settings: zero issues.

## 3. Deployment

Hosted on cPanel via Phusion Passenger (`passenger_wsgi.py` → `config.settings.prod`). Standard deploy from here on:

```bash
git pull origin main
pip install -r requirements/prod.txt
python manage.py migrate            # only if new migrations exist
python manage.py collectstatic --noinput
touch tmp/restart.txt
```

A Tailwind rebuild (`python manage.py tailwind build`) is **no longer part of the deploy** — the compiled CSS ships in git (see above).

## 4. Known gaps / open items

- **SMTP was never fully set up or tested.** Local dev uses the console email backend; real SMTP credentials (`EMAIL_HOST`/`PORT`/`USER`/`PASSWORD`) were never added to `.env`, and this was left as an open thread earlier in the project.
- **Privacy Policy operator name is a placeholder** — needs a real legal entity/individual name before the legal pages offer real protection.
- **Only Kathmandu Metropolitan City is seeded as a municipality** (out of the full 753 in Nepal) — enough for the 3 seeded processes' office references, not a complete location dataset.
- **No formal age verification** on registration — the Terms state a 16+ minimum, but nothing technically enforces it.
- **`ROADMAP.md` and `README.md` are now stale** in a few places (Django version, `ne`→`np` locale rename, missing `tourism`/`dashboard` apps, pre-security-hardening/pre-legal-pages state) — worth a pass to bring current, not done as part of this report.
- Whether the latest pushes (legal pages, security hardening) are actually live on production depends on whether the deploy steps above have been run since — this report reflects what's in the `main` branch on GitHub, not a live-site check.

## 5. Verification discipline used throughout

Every feature above went through the same loop before being considered done: `manage.py check`, a full `manage.py test` run, a live Playwright pass against the real dev server (including mobile viewport and the Nepali locale), and an i18n sweep (`makemessages` → translate every new string → `msgfmt --check` → `compilemessages` → verify live). Nothing here is "should work" — everything was actually run and observed working.
