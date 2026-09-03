# HamroNepal.com — Build Roadmap

**HamroNepal = Nepal's Everyday Digital Life Platform.** Not a blog, not a news site, not a directory, not a calculator collection, not an AI wrapper. It is a "Process OS" for Nepal: users tell it what they're trying to accomplish (register a company, renew a license, buy land) and it turns that into a structured, sourced, trackable process — checklist, requirements, fees, official links, progress tracking — rather than just another article explaining the process.

This document is the source of truth for the build. It divides the current build target — the **V1 Foundation** — into sequential phases. Check items off as they're completed. A **Future Phases** section at the end summarizes the wider product vision (V2/V3/V4) for context; nothing there is being built yet.

## ✅ V1 Foundation — complete

All 11 phases below are done: a working Django app with real Nepal government process data, English/Nepali content, full progress tracking, a personal dashboard, an admin CMS with source-verification and versioning, 71 passing tests, and SEO/deploy checks clean. Run it locally per [README.md](README.md). See **Future Phases** at the end of this document for what's deliberately not built yet.

## V1 Foundation — scope

- Full Django project scaffold: all core apps needed to run the Process Engine end-to-end.
- Normalized data model, admin CMS, authentication, i18n (English + Nepali), homepage + search, and full progress tracking.
- Only **2–3 fully worked example processes**, built from real, web-researched, source-cited Nepal government data — not the full 20–30 process catalog, and never fabricated facts.
- Frontend: Django templates + HTMX + Tailwind CSS (server-rendered, no separate SPA/API layer).
- Confirmed local toolchain: Python 3.14.6, Django 6.1, PostgreSQL, Redis.

Full architectural detail (data model, URL map, security model, etc.) lives in the approved build plan; this file tracks execution phase by phase.

---

## Phase 1 — Project Setup & Tooling ✅

**Goal:** a running, checked-out Django project wired to Postgres, with dependencies pinned and secrets externalized.

- [x] `django-admin startproject config .`, restructured into `config/settings/{base,dev,prod}.py`
- [x] `django-environ` + `.env` / `.env.example`; git init + `.gitignore` (`.env` confirmed excluded from tracking)
- [x] `requirements/base.txt`: Django 6.1, `psycopg[binary]`, `django-environ`, `django-htmx`, `django-modeltranslation`, `django-tailwind`, `django-redis`, `django-ratelimit`, `Pillow`
- [x] `requirements/dev.txt`: `django-debug-toolbar`, `factory_boy` (+ `Faker`, its dependency)
- [x] Local Postgres DB `hamronepal_dev` created, `DATABASE_URL` wired via `.env`
- [x] `manage.py check` passes; `runserver` boots and serves `/admin/login/` (200 OK)

Notes:
- Python virtualenv at `.venv/` (gitignored); activate with `source .venv/bin/activate`.
- `django.contrib.postgres`, Redis cache (`django-redis`), and `django.contrib.sitemaps` are already wired in `base.py` since they're zero-cost config; they'll start being *used* in later phases (search, caching, sitemap).
- Django 6.1 uses the new `MAILERS` setting (not `EMAIL_BACKEND`, which is deprecated toward Django 7.0) — console backend in dev, SMTP-via-env in prod.
- `TIME_ZONE` set to `Asia/Kathmandu`.
- **Important sequencing note:** an initial `migrate` was run and then rolled back (db dropped/recreated) before this phase finished, because it would have created tables against Django's stock `auth.User` — which conflicts with the plan's rule that `AUTH_USER_MODEL` must be set *before* the first real migration. The `hamronepal_dev` database is confirmed empty; Phase 2 must set `AUTH_USER_MODEL = "accounts.User"` before running `migrate` for the first time.
- No commits made yet — repo is initialized and staged-ready, first commit left for the user's discretion.

**Depends on:** nothing (first phase).

---

## Phase 2 — Core Data Models ✅

**Goal:** the full normalized schema behind the Process Engine, migrated cleanly.

- [x] `apps/accounts` — custom `User` (email as `USERNAME_FIELD`, custom `UserManager`), `Profile`. `AUTH_USER_MODEL` set before the first migration ever ran.
- [x] `apps/locations` — `Province` → `District` → `Municipality` → `Ward`
- [x] `apps/organizations` — `GovernmentOrganization`, `GovernmentOffice`
- [x] `apps/processes` — `ProcessCategory`, `Process`, `ProcessStep`, `ProcessRequirement`, `ProcessSource`, `ProcessVersion`, `UserProcessProgress`, `UserStepProgress`, `UserRequirementProgress`
- [x] `apps/tasks` — `Task`, `Reminder`
- [x] `apps/core` — shared abstract `TimeStampedModel` (`created_at`/`updated_at`) all other models inherit from
- [x] `makemigrations` (single pass across all six apps — Django's autodetector resolved the cross-app FK dependencies, e.g. `accounts.Profile → locations.Municipality`, on its own) then one `migrate`

Notes:
- Apps registered as `apps.core`, `apps.accounts`, `apps.locations`, `apps.organizations`, `apps.processes`, `apps.tasks` in `INSTALLED_APPS`; app labels stay the short form (`accounts`, `processes`, ...), so FK references use e.g. `"processes.Process"`, and `AUTH_USER_MODEL = "accounts.User"`.
- `ProcessVariant` (all/individual/business) lives in `apps/processes/models.py` and is shared by `ProcessStep.variant`, `ProcessRequirement.variant`, and `UserProcessProgress.variant_selected` — the entire conditional-path mechanism, as designed.
- `locations`/`organizations` models carry manual `name`/`name_ne` fields (stable, low-churn reference data). `processes` app models (`Process`, `ProcessStep`, `ProcessRequirement`, `ProcessCategory`) deliberately have single untranslated text fields for now — `django-modeltranslation` will generate `_en`/`_ne` shadow fields for those in Phase 3/10, not duplicated by hand here.
- Verified with a full shell-level walk of the model graph: created a `User`, a full `Province → District → Municipality → Ward` chain, a `GovernmentOrganization`/`GovernmentOffice`, a complete `ProcessCategory → Process → ProcessStep → ProcessRequirement → ProcessSource` graph, a `UserProcessProgress` row, and a `Task`/`Reminder` — all relationships resolved correctly. `GovernmentOffice.municipality`'s `on_delete=PROTECT` correctly blocked deleting a `Province` still in use, confirming that guardrail works; the throwaway test data was then cleared by resetting the dev database rather than deleting through the protected chain.
- `manage.py check`, `makemigrations --check --dry-run` (no drift), and `migrate` on a fresh `hamronepal_dev` all pass cleanly.

**Depends on:** Phase 1.

---

## Phase 3 — Admin CMS ✅

**Goal:** staff can create, edit, verify, and publish process content without touching code.

- [x] Wire `django-modeltranslation` for bilingual content fields
- [x] Register all models in Django admin
- [x] `ProcessAdmin` with inline Step / Requirement / Source formsets
- [x] Custom action: **"Mark sources verified today"**
- [x] Custom action: **"Publish new version"** (requires ≥1 `ProcessSource`; writes a `ProcessVersion` snapshot)
- [x] `createsuperuser`; sanity-checked full CRUD on a dummy process end-to-end

Notes:
- `modeltranslation` registered (`apps/processes/translation.py`) on `Process`, `ProcessStep`, `ProcessRequirement`, `ProcessCategory` — generates `_en`/`_ne` shadow fields (migration `processes/0002_...`); `slug` stays untranslated (same URL across languages). `modeltranslation` sits before `django.contrib.admin` in `INSTALLED_APPS` as required.
- `apps/processes/services.py` now holds `publish_new_version(process, user, changelog="")` — serializes the process/steps/requirements/sources into a `ProcessVersion.snapshot`, refuses to publish with zero sources (`PublishError`), and bumps `status`/`current_version_number`/`last_verified_at`/`last_verified_by`. Called from the admin action, not a signal.
- `accounts` admin uses a proper email-based `UserAdmin` (no `username`) with a `Profile` inline.
- `UserProcessProgressAdmin` and `ProcessVersionAdmin` registered read-only (support/audit visibility only), with read-only inlines for step/requirement progress.
- Verified with a scripted Django test-`Client` run logged in as a real staff user: process change page rendered all three inlines; publishing a sourceless process was correctly blocked with the guardrail error; "Mark sources verified today" stamped the source; publishing afterward created a real `ProcessVersion` with a populated snapshot and moved the process to `published`; the read-only progress page rendered. Test data cleared via a dev-database reset.
- `manage.py check` and `makemigrations --check --dry-run` both clean.

**Depends on:** Phase 2.

---

## Phase 4 — Authentication & Accounts ✅

**Goal:** a user can register, verify their email, log in, and manage their profile.

- [x] Register / login / logout views
- [x] Email verification flow (console backend in dev)
- [x] Password reset flow
- [x] Profile edit view
- [x] `django-ratelimit` on login, register, password-reset-request

Notes:
- All app-facing URLs now wrapped in `i18n_patterns()` (`config/urls.py`) — accounts routes live at `/en/accounts/...` and `/ne/accounts/...`; `/admin/`, `/__debug__/`, and `/i18n/setlang/` stay unprefixed. `/i18n/` (language switcher endpoint) is wired now even though nothing uses it until Phase 5's nav.
- Registration uses Django's stock `UserCreationForm` (subclassed for our email-only `User`) and logs the user in immediately; `email_verified` starts `False` and flips `True` via a emailed link using a custom one-time token (`apps/accounts/tokens.py`, a `PasswordResetTokenGenerator` subclass keyed off `email_verified` so a token can't be replayed after it's used).
- Login/password-reset reuse Django's built-in `auth_views` classes with custom templates; `django_ratelimit` applied via `method_decorator(..., name="dispatch")` on the class-based views and a plain decorator on the function-based register view (10/min register & login, 5/min password-reset-request, keyed by IP, `block=True`).
- Profile editing (`accounts:profile`) saves two forms in one page — `UserPreferencesForm` (phone/preferred language) and `ProfileForm` (display name/bio/avatar/municipality) — using form `prefix` to avoid field-name collisions.
- Django 6.1's new `MAILERS` setting (not the deprecated `EMAIL_BACKEND`) is confirmed to work transparently with `user.email_user()` / `send_mail()` / `PasswordResetView`.
- `templates/base.html` created as a deliberately minimal, unstyled shell (`{% block content %}`) so accounts templates have something to extend without waiting on Phase 5's design system; Phase 5 will restyle it in place, not restructure it.
- Verified with a full scripted flow via Django's test client (`locmem` email backend to capture messages): register → user logged in, verification email sent → click link → `email_verified` flips True (and is safely idempotent on reuse) → wrong password rejected, correct password logs in → profile form saves both sub-forms correctly → password-reset email sent → reset link followed → new password accepted → old password now rejected, new one works → 6 rapid password-reset requests correctly return `403` starting at the 5/min limit. Test data cleared via a dev-database reset.
- `manage.py check` and `makemigrations --check --dry-run` both clean.

**Depends on:** Phase 2 (custom `User` model).

---

## Phase 5 — Design System & Templates ✅

**Goal:** a shared visual language and page shell ready for real pages.

- [x] `django-tailwind init`, brand colors / theme tokens
- [x] `base.html` wired with Tailwind + HTMX + CSRF header snippet (`htmx:configRequest`)
- [x] Shared components: navbar (with language switcher), footer, `process_card.html`

Notes:
- `theme` app created via `python manage.py tailwind init --tailwind-version 4s` — the **standalone** Tailwind v4 template, which uses `pytailwindcss` to download a self-contained `tailwindcss` CLI binary (outside the repo) instead of requiring Node/npm. `python manage.py tailwind build` compiles `theme/static_src/src/styles.css` → `theme/static/css/dist/styles.css` (gitignored, already covered by Phase 1's `.gitignore`); `tailwind start` watches for dev. The demo `theme/templates/base.html` cookiecutter shipped was deleted — our own `templates/base.html` (project-root `DIRS`) already shadows it and is the real one.
- Tailwind v4 config is CSS-first (no `tailwind.config.js`); brand tokens (`--color-brand-*`, `--color-accent-*`) are declared directly in `styles.css` via `@theme`. `cookiecutter` (a one-time dependency of the `tailwind init` scaffolding command only) was **not** added to `requirements/` — it isn't needed at runtime or in future dev setup.
- HTMX is vendored at `static/vendor/htmx.min.js` (not loaded from a CDN) for reliability in production; loaded in `base.html` with `defer`, plus an `htmx:configRequest` listener that attaches the `X-CSRFToken` header from the `csrftoken` cookie so HTMX POSTs will work once Phase 7 adds them.
- `base.html` now the real shell: Tailwind stylesheet, HTMX script, navbar/footer includes, a styled messages block (color keyed off `message.tags`), and `{% block content %}`/`{% block extra_js %}`/`{% block meta %}` for pages to hook into.
- `apps/core/forms.py::TailwindFormMixin` centralizes input styling so any current or future Django form gets consistent Tailwind classes by inheriting it (skips checkbox/radio widgets, which need different treatment). Applied to every accounts form — including thin subclasses of Django's built-in `AuthenticationForm`/`PasswordResetForm`/`SetPasswordForm` so the stock auth views stay stock but still render styled.
- All Phase 4 accounts templates restyled in place (not restructured) to actually use the new design system, rather than leaving Phase 4's bare HTML unstyled indefinitely.
- Found and fixed a real bug while verifying: `<html lang="{{ LANGUAGE_CODE }}">` was rendering as `lang=""` because `django.template.context_processors.i18n` was missing from `TEMPLATES` — added it; confirmed `lang="en"` / `lang="ne"` now render correctly per locale.
- Verified: rebuilt Tailwind CSS and confirmed brand utility classes (`bg-brand-600`, etc.) actually compiled in; booted `runserver` and confirmed login/register/password-reset pages return 200 with the stylesheet and htmx.min.js both linked and loading; re-ran the full Phase 4 auth regression script (register → verify → login → profile → password reset → rate limit) against the restyled templates/forms — all still pass; `collectstatic --dry-run` succeeds. Test data cleared via a dev-database reset.

**Depends on:** Phase 1.

---

## Phase 6 — Homepage & Search ✅

**Goal:** "What are you trying to do?" — the platform's core discovery moment, working end-to-end.

- [x] Homepage: large intent search box + example prompts (register a company, renew my license, buy a vehicle, go abroad, rent a house)
- [x] Postgres full-text search (`SearchVector`/`SearchQuery`/`SearchRank` + GIN index)
- [x] HTMX live search results

Notes:
- `apps/core` now owns the homepage (`/`, name `core:home`); `apps/processes` owns `search/` and `processes/<slug>/` — both mounted at the URL root (inside `i18n_patterns`) per the original URL map, so they read as `/en/search/`, `/en/processes/<slug>/`, etc.
- `Process` gained two persisted, indexed columns — `search_vector_en`/`search_vector_ne` (`SearchVectorField` + `GinIndex` each) — rather than computing a `SearchVector` on the fly per request. They're recomputed in `services.publish_new_version()` right after a version is published (weighted A/B/C across title/summary/description), which has a deliberate side effect: **only published, sourced content is ever searchable** — drafts don't get indexed at all, matching the platform's trust principle (§30 of the spec) for free rather than needing a separate "is this safe to show" check in the view.
- English search uses Postgres's `"english"` text-search config (stemming); Nepali uses `"simple"` (tokenization only, no stemming) since Postgres ships no Nepali linguistic config — an honest limitation, not pretended-away.
- The search view serves the same URL as both a full page (`processes/search_results.html`) and an HTMX partial (`processes/partials/_search_results.html`), branching on `request.htmx` (via `django_htmx`) — the homepage's search box and the search page's own input both `hx-get` into `#search-results` live, and also work with zero JavaScript via a normal form GET (progressive enhancement, no dead-end for non-JS/HTMX-blocked clients).
- Added a genuinely minimal `processes/<slug>/` detail view/template now (not full Phase 7 scope) purely so `components/process_card.html` (built in Phase 5) has somewhere real to link to instead of a dead `NoReverseMatch` — same "lightweight seed now, Phase 7 fully builds it out" pattern already used for `base.html` in Phase 4→5. It's explicit in the template ("Full step-by-step requirements and progress tracking... coming soon") rather than pretending to be finished.
- Fixed a bug found while wiring links: the navbar's brand link was a bare `href="/"`, which under `i18n_patterns` needs an extra redirect hop through `LocaleMiddleware` to reach `/en/`; changed to `{% url 'core:home' %}` so it resolves straight to the correct locale-prefixed URL.
- Verified end-to-end: seeded one published English process, one published Nepali-content process, and one intentionally unpublished draft, then via Django's test client confirmed — homepage renders with all example prompts; searching finds the published process and never the draft; an `HX-Request` header correctly returns a bare partial (no `<html>`/navbar) instead of the full page; a no-match query renders the empty state; the published process's detail page renders while the draft's correctly 404s; Nepali-language search matches Nepali content under `/ne/search/`. Test data cleared via a dev-database reset.
- `manage.py check` and `makemigrations --check --dry-run` both clean.

**Depends on:** Phases 2, 5.

---

## Phase 7 — Process Engine: Detail & Tracking ✅

**Goal:** the actual differentiator — a process page that can be tracked, not just read.

- [x] Process list + category filter
- [x] Process detail page: steps, requirements, fees, sources, FAQs, JSON-LD `HowTo`, SEO meta tags
- [x] `services.start_tracking(user, process, variant)`
- [x] Track-progress view/template with per-step/requirement checklist
- [x] HTMX toggle endpoints for steps and requirements
- [x] Status-transition logic (not started → preparing → applied → processing → completed)
- [x] Individual/business variant selection where applicable

Notes:
- Added a `ProcessFAQ` model (question/answer/order, modeltranslation-registered, inlined in `ProcessAdmin`, included in publish snapshots) — the schema promised FAQs as part of a process's structure but no model existed for it yet; this phase's detail page needed it for real.
- `services.py` gained the actual Process Engine tracking logic: `start_tracking()` (variant-filtered, idempotent via `get_or_create`), `toggle_step_progress()`/`toggle_requirement_progress()` (flip completion, stamp `completed_at`, and auto-advance `not_started → preparing` the moment anything is first checked), and `advance_status()` for the milestone stages. Deliberately **not** auto-completing from the checklist: finishing the prep checklist means "ready to apply," not "process complete" — `preparing → applied → processing → completed` are real-world milestones the user declares explicitly (a status dropdown on the tracking page), since nothing in our system can observe a government office actually processing an application.
- `apps/processes/seo.py` builds `HowTo` (steps → `HowToStep`, duration → ISO 8601 `totalTime`, summed step fees → `estimatedCost`) and `FAQPage` JSON-LD, safely embedded via a hand-rolled escaper (`</` → `<\/`) rather than Django's `json_script` filter, which hardcodes `type="application/json"` instead of the `application/ld+json` structured-data crawlers actually look for.
- The variant mechanism designed back in Phase 2 got its first real exercise: a process with any non-`all`-variant step/requirement shows an individual/business picker before "Start tracking" is allowed; `start_tracking()` then only creates progress rows for steps/requirements matching `all` or the chosen variant — verified a business-only step is correctly excluded from an individual applicant's checklist (and vice versa).
- Process detail is reachable at `/processes/<slug>/`, with `/processes/` as the category-filterable list — both were stubbed minimally in Phase 6 and are now fully built out per the original URL map, alongside `/processes/<slug>/start/`, `/track/`, `/track/advance/`, and the two per-item `/track/.../toggle/` HTMX endpoints.
- Verified end-to-end via Django's test client: anonymous visitors see both JSON-LD blocks and a login prompt instead of a start form (and get redirected to login on a direct POST); an authenticated user is shown the variant picker, is blocked from starting without picking one, and starting creates exactly the right variant-filtered rows; starting twice is a no-op; toggling a step/requirement via a simulated `HX-Request` returns a bare partial and correctly flips `not_started → preparing` (and un-toggling does **not** revert status); manually advancing through `applied → completed` stamps `completed_at`; a second user tracking the same process gets fully independent, correctly variant-filtered progress without touching the first user's data; an unpublished draft's detail page and start endpoint both correctly 404. Test data cleared via a dev-database reset.
- `manage.py check`, `makemigrations --check --dry-run`, and `collectstatic --dry-run` all clean.

**Depends on:** Phases 2, 3, 5.

---

## Phase 8 — Dashboard & Tasks ✅

**Goal:** a personal home base showing active processes and to-dos at a glance.

- [x] `/dashboard/`: active `UserProcessProgress` rows with progress bars
- [x] `Task` CRUD (create, complete, delete)
- [x] Upcoming items surfaced (due tasks; reminders shown but not yet sent — no delivery pipeline in V1)

Notes:
- `apps/processes/services.py::compute_percent()` extracted from Phase 7's `track_progress_view` (it was duplicating the same completed/total math inline) so the dashboard's per-process progress bars and the tracking page's progress bar share one implementation.
- `apps/tasks/services.py::toggle_completed()` added for symmetry with the processes app's toggle functions — even a two-line state flip goes through a service function here, not inline in the view, matching the pattern established since Phase 3.
- Task create/toggle/delete all enforce `user=request.user` in their `get_object_or_404`/queryset filters — verified a second user gets a 404 (not a silent no-op) trying to toggle or delete someone else's task.
- The dashboard only lists `UserProcessProgress` rows excluding `status=completed` as "active"; completed ones roll into a simple count instead, so the dashboard doesn't accumulate stale finished processes over time.
- **`LOGIN_REDIRECT_URL` changed from `accounts:profile` to `core:dashboard`**, and registration/profile-save now redirect to the dashboard too (email verification still redirects to the profile page specifically, since that's where the verified/not-verified badge actually lives) — now that a real personal home base exists, it's the natural post-login landing page per the product vision's "My Nepal" concept, rather than the profile-settings page.
- "Reminders shown but not yet sent" from the checklist is satisfied via `Task.due_date` surfaced in a "Coming up" box — the `Reminder` model itself still has no creation UI or delivery pipeline (unchanged from Phase 2/4 scope; still explicitly a later phase).
- Verified end-to-end: anonymous `/dashboard/` access redirects to login; login now lands on the dashboard; the empty-state dashboard renders correctly; starting to track a process makes it appear with a live progress bar that updates as checklist items are toggled; marking a process `completed` correctly drops it from the active list into the completed count; the quick-add task form creates a task that shows in both the task list and the "Coming up" box; toggling and deleting via HTMX work and are scoped per-user (a second user gets `404`, not access). Test data cleared via a dev-database reset.
- `manage.py check`, `makemigrations --check --dry-run` (no model changes this phase), and `collectstatic --dry-run` all clean.

**Depends on:** Phases 4, 7.

---

## Phase 9 — Content Seeding ✅

**Goal:** the 2–3 example processes are real, sourced, and trustworthy — not placeholders.

- [x] Seed all 7 provinces + 77 districts; seed municipalities/wards only for offices the example processes reference
- [x] Pick final 2–3 processes (Company Registration, PAN Registration, Passport Application — all three built, not just 2)
- [x] Research each process via its official source(s): steps, requirements, fees, responsible authority
- [x] Enter content; attach ≥1 `ProcessSource` per process with URL + last-verified date
- [x] Manually cross-check every fact against its cited source before publishing
- [x] Run "Publish new version" — confirm first `ProcessVersion` created

Notes:
- Content entered via two idempotent management commands (`seed_locations`, `seed_processes`) rather than the admin UI by hand — the same code path (ORM + `services.publish_new_version()`) the admin actions use, just scripted so it's re-runnable and reviewable as a diff instead of a one-off manual data-entry session. `seed_processes` requires a superuser to exist (used as the publishing user) and `seed_locations` to have run first (needs Kathmandu Metropolitan City for the three offices).
- All three processes researched from **primary Nepal government sources**, fetched directly (not just cited secondhand): [ocr.gov.np](https://ocr.gov.np/) + its fee schedule at `/pages/revenue/` (Office of the Company Registrar), [ird.gov.np](https://ird.gov.np/) (Inland Revenue Department), and [nepalpassport.gov.np](https://nepalpassport.gov.np/) + its fee (`/process/-41`) and process (`/process/-1`) pages (Department of Passports). Every `ProcessSource` carries the real URL and today's date as `last_verified_date`.
- **A real trust-relevant discrepancy was found and handled honestly**: multiple third-party legal/consultancy blogs consistently reported Nepali passport fees as NPR 5,000/10,000 (34/66-page, "normal"), but fetching the government's own fee page directly showed NPR 12,000/20,000 for a new/renewal adult passport (with separate, higher tiers for lost/damaged replacements). Per this platform's own trust rule — primary sources over aggregator consensus — the seeded content uses the government page's figures, and both the `ProcessSource.notes` and a dedicated FAQ entry explicitly flag that other tiers exist and point users to the official schedule rather than asserting one oversimplified number.
- District/province `code` values are Claude-assigned internal identifiers (e.g. `bagmati-05`), not official government codes — the model never claims otherwise; only province/district **names** and the process content itself carry sourced factual claims.
- Two real bugs surfaced and fixed while seeding: (1) `Sudurpashchim Province`'s code was too long for `Province.code`'s `max_length=10` — shortened to `sudur`; (2) Postgres's English stemmer treats "register" and "registration" (and "apply"/"application") as *different* stems, so a title like "Register a Private Limited Company" silently failed to match the very natural search "company registration" — fixed by naturally working the noun form into each process's summary text (confirmed via direct `tsquery` testing, not just re-running the app and hoping) rather than papering over it.
- Verified end-to-end: both seed commands are fully idempotent (a second run creates zero duplicates); the process list shows all three; search correctly finds each process by natural-language queries including the exact phrasing used in the homepage's own example prompts; each detail page renders its JSON-LD, cited official sources, and researched fee/document content correctly. This seeded content is **real data, not test fixtures** — it was intentionally left in the dev database rather than cleared.
- `manage.py check` and `makemigrations --check --dry-run` clean.

**Depends on:** Phases 2, 3.

---

## Phase 10 — Internationalization ✅

**Goal:** the platform genuinely works in both English and Nepali, not just UI labels.

- [x] `makemessages -l ne`; translate UI chrome strings; `compilemessages`
- [x] Verify `/en/...` and `/ne/...` both render correctly — UI chrome and process content
- [x] `hreflang` alternates between language versions of process pages

Notes:
- All 123 extracted UI-chrome strings translated into Nepali by hand (`locale/ne/LC_MESSAGES/django.po` → compiled `.mo`) — covering every template, view message, and email. `compilemessages` also compiled Django's own bundled `ne` translations for `contrib.admin`/`auth`/etc., so the Django admin itself is now partly Nepali too, as a free side effect.
- **Found and fixed a real gap `makemessages` couldn't catch on its own**: every model `TextChoices` label (`UserProcessProgress.Status`, `ProcessVariant`, `Process.Status`, `Municipality.MunicipalityType`, `GovernmentOrganization.OrganizationType`, `Reminder.Channel`) was a plain Python string, not wrapped in `gettext_lazy` — so `get_status_display()` etc. would have silently stayed in English on `/ne/` pages forever, since these labels never go through template `{% translate %}` tags at all. Wrapped all of them across `apps/processes`, `apps/locations`, `apps/organizations`, `apps/tasks` (confirmed no migration was generated — Django doesn't treat a lazy-translated choice label as a schema change); `accounts.User.Language` was deliberately left alone since language names are shown as endonyms ("English"/"नेपाली"), not translated.
- **Translated the actual seeded process content**, not just UI chrome — both categories and all three processes' `title`, `summary`, `description`, `eligibility`, `estimated_duration_note`, `total_fee_note`, `meta_title`/`meta_description`, every step/requirement/FAQ. This is what the phase's "chrome + process content" goal actually asks for, and it's the only way `/ne/processes/...` pages are genuinely usable rather than technically-bilingual-but-empty.
- Added `MODELTRANSLATION_FALLBACK_LANGUAGES = ("en", "ne")` — without it, any process (present or future) missing a Nepali translation for a field would render **blank** on `/ne/` instead of falling back to whatever language it does have. This is a permanent, structural safeguard, not just a fix for today's three processes — verified directly by publishing a deliberately Nepali-untranslated test process and confirming it shows its English content on `/ne/` rather than empty fields.
- `hreflang` alternates added to process detail pages via `django.urls.translate_url()` (the URL-based per-language conversion path Django provides for exactly this) rather than hand-built string substitution — correct even if URL structure changes later.
- Verified end-to-end: English and Nepali chrome both render correctly (including `<html lang="ne">`); all three processes' titles/categories/steps/FAQs render in Nepali; the `UserProcessProgress` status badge on the tracking page shows the translated label ("सुरु नभएको" for "Not Started"); `hreflang="en"`/`hreflang="ne"` links are present and point at the correct absolute URLs; a Nepali-untranslated process correctly falls back to English instead of rendering blank. Test artifacts (a throwaway user and process) were cleared; the three real seeded processes and their translations were left in place and confirmed intact afterward.
- `manage.py check` and `makemigrations --check --dry-run` both clean.

**Depends on:** Phases 5, 6, 7, 9 (needs real content to translate against).

---

## Phase 11 — Testing, SEO & Docs ✅

**Goal:** the build is verified, crawlable, and handoff-ready.

- [x] Model tests, service tests, view tests (auth gating, HTMX partials, search)
- [x] One full smoke test: anonymous → registered → track → complete a process
- [x] `manage.py check --deploy` clean
- [x] `sitemap.xml`, `robots.txt`, custom 404/500 templates
- [x] `README.md` with setup and run instructions
- [x] CSRF enforcement and rate-limiting confirmed — now as permanent automated tests, not just manual checks

Notes:
- **71 permanent tests** now live under each app's `tests/` package (replacing the throwaway `manage.py shell` verification scripts used while building earlier phases): `apps/accounts` (User manager, registration, email verification incl. idempotency, login, password reset, profile, rate limits), `apps/processes` (models; `services.py` — publish/`PublishError`, `start_tracking` variant-filtering and idempotency and per-user isolation, toggle + status-transition logic, `compute_percent`; views — search incl. HTMX-partial-vs-full-page and draft exclusion, process list/category filter, process detail incl. JSON-LD and hreflang, the full tracking flow incl. ownership checks), `apps/tasks` (toggle service, CRUD incl. cross-user isolation), `apps/core` (home, dashboard, error pages, sitemap/robots, CSRF). `factory_boy` (installed since Phase 1 for exactly this) builds the deep fixture graphs for `apps/accounts` and `apps/processes`.
- The CSRF and rate-limit checks are real automated tests now, not just things verified once by hand mid-build: `Client(enforce_csrf_checks=True)` (Django's test client skips CSRF checks *by default*, which would silently hide a real regression) confirms an unauthenticated-token POST gets a `403`; rate-limit tests drive each limited endpoint past its threshold and assert the cutoff.
- `manage.py check --deploy` run against `config.settings.prod` (with representative env vars supplied inline, since `prod.py` intentionally has no defaults for things like `EMAIL_HOST`) comes back clean using the actual Phase 1-generated `SECRET_KEY` — confirmed HSTS/SSL-redirect/secure-cookie settings are all correctly picked up.
- `apps/processes/sitemaps.py` — `ProcessSitemap` lists only `status=published` processes (verified a draft never appears), `StaticViewSitemap` covers the homepage and process list; both registered at `/sitemap.xml` (outside `i18n_patterns`, so it's a single canonical listing, not per-locale). `/robots.txt` disallows `/admin/`, `/accounts/`, `/dashboard/` and points crawlers at the sitemap.
- Custom `404.html` extends `base.html` normally (Django *does* run context processors for the 404 handler, so this is safe). `500.html` deliberately does **not** extend `base.html` — Django renders the 500 page with no request/context at all, specifically so a broken context processor can't also break the error page — so it's fully self-contained inline HTML with no template-tag dependencies, tested by mounting a deliberately-broken view on a throwaway test-only urlconf (`apps/core/tests/urls_error_test.py`) and hitting it with `Client(raise_request_exception=False)`.
- `manage.py test`, `check`, `check --deploy`, `makemigrations --check --dry-run`, and `collectstatic --dry-run` all clean. `git status` confirmed `.venv/`, `staticfiles/`, and `theme/static/css/dist/` all correctly stay untracked while the vendored `static/vendor/htmx.min.js` correctly does not.

**Depends on:** all prior phases.

---

## Future Phases (not built in V1 — for context only)

**V2:** personal document vault (encrypted, private-by-default), Life Events journeys (moving, buying a vehicle, going abroad, buying a house), household workspace, location-aware process variations, community process experiences, information-verification system, verified provider network, "Ask a Local Expert" Q&A, richer notification delivery (email/push/SMS).

**V3:** AI process assistant (interface only, cites underlying HamroNepal sources — never invents requirements), automatic document metadata extraction, advanced next-step recommendations, provider marketplace with lead generation, business/compliance workspace, public HamroNepal API, mobile/PWA experience.

**V4:** the full Nepal Process Graph — citizens, businesses, and verified providers connected through government organizations, documents, and services, exposed as infrastructure via the HamroNepal API.
