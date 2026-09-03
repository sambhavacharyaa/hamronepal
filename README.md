# HamroNepal.com

**Nepal's Everyday Digital Life Platform.** A "Process OS" for Nepal — instead of just explaining how to register a company or renew a passport, HamroNepal turns that into a structured, sourced, trackable process: a personalized checklist, official fees and documents, and progress tracking from start to finish.

See [ROADMAP.md](ROADMAP.md) for the full build plan and current progress.

## Stack

- **Backend:** Django 6.1, PostgreSQL, Redis (cache)
- **Frontend:** Django templates + HTMX + Tailwind CSS v4 (standalone CLI, no Node/npm required)
- **i18n:** English + Nepali (`django-modeltranslation` for content, standard `gettext` for UI chrome)

## Prerequisites

- Python 3.12+
- PostgreSQL (running locally, e.g. via Homebrew: `brew services start postgresql@16`)
- Redis (running locally, e.g. via Homebrew: `brew services start redis`)

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements/dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — at minimum, generate a real SECRET_KEY and confirm DATABASE_URL/REDIS_URL

# 4. Create the database
createdb hamronepal_dev

# 5. Run migrations
python manage.py migrate

# 6. Create an admin account
python manage.py createsuperuser

# 7. Seed reference data and example content
python manage.py seed_locations    # 7 provinces, 77 districts, Kathmandu Metropolitan City
python manage.py seed_processes    # 3 real, source-cited example processes (requires a superuser)

# 8. Compile translations (already committed, but re-run after editing locale/ne/LC_MESSAGES/django.po)
python manage.py compilemessages

# 9. Build Tailwind CSS once (first run only — downloads the standalone tailwindcss binary)
python manage.py tailwind install
python manage.py tailwind build
```

## Running locally

Two terminals, both with the virtualenv activated:

```bash
# Terminal 1 — Django dev server
python manage.py runserver

# Terminal 2 — Tailwind watcher (rebuilds CSS as templates change)
python manage.py tailwind start
```

Visit `http://127.0.0.1:8000/` (redirects to `/en/`). Django admin is at `/admin/`. Switch to Nepali via the language selector in the navbar, or visit `/ne/` directly.

## Running tests

```bash
python manage.py test
```

Tests use their own throwaway database (created and destroyed automatically) and a local-memory cache/email backend where needed — they don't touch the dev database or send real email.

## Project structure

```
config/               Django project settings, root URLconf
apps/
  core/                homepage, dashboard, robots.txt
  accounts/            custom email-based User, auth, profile
  locations/            Province → District → Municipality → Ward
  organizations/         GovernmentOrganization, GovernmentOffice
  processes/            the Process Engine — Process/Step/Requirement/Source/FAQ/Version,
                         tracking, search, admin CMS, seed commands
  tasks/                 personal Task/Reminder
theme/                  django-tailwind app (styles.css, compiled CSS output)
templates/              shared base.html, components/, per-app templates
locale/ne/               Nepali translations
```

Each app owns its `models.py`, `services.py` (business logic — publishing, tracking, status
transitions), `views.py`, `urls.py`, `admin.py`, and `tests/`.

## Admin CMS

Staff can create/edit processes (with inline steps, requirements, sources, and FAQs) at
`/admin/`. Two custom actions matter for content trust:

- **"Mark sources verified today"** (on a `ProcessSource`) — stamps `last_verified_date`.
- **"Publish new version"** (on a `Process`) — refuses to publish a process with zero cited
  sources, and snapshots the full process into a versioned `ProcessVersion` record.

## Content policy

Every process must cite at least one official source before it can be published — this is
enforced in code (`apps/processes/services.py::publish_new_version`), not just by convention.
Seeded example content is real data researched from official Nepal government sources
(see `apps/processes/management/commands/seed_processes.py` and the `ProcessSource` entries
it creates); nothing is fabricated or placeholder.

## Internationalization workflow

UI chrome strings live in `locale/ne/LC_MESSAGES/django.po`. After adding new `{% translate %}`
tags or `gettext_lazy(...)` calls:

```bash
python manage.py makemessages -l ne --ignore=".venv/*" --ignore="staticfiles/*" --ignore="theme/static_src/*"
# translate any new, empty msgstr entries in locale/ne/LC_MESSAGES/django.po
python manage.py compilemessages
```

Process *content* (titles, descriptions, steps, etc.) is translated per-record via
`django-modeltranslation`'s `_en`/`_ne` fields, editable directly in the admin.
`MODELTRANSLATION_FALLBACK_LANGUAGES` means untranslated Nepali content falls back to English
rather than rendering blank.
