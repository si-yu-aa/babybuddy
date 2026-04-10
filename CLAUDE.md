# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Baby Buddy is a Django 5.1 application for caregivers to track baby sleep, feedings, diaper changes, tummy time, and more. It uses a template-based frontend (Bootstrap 5 + vanilla JS/jQuery) alongside a Django REST Framework API.

## Tech Stack

- **Backend**: Django 5.1, Django REST Framework, Python 3.10-3.12
- **Frontend**: Bootstrap 5, Sass/SCSS, vanilla JavaScript with jQuery
- **Build**: Gulp (asset pipeline), Pipenv (Python dependencies), npm (JS dependencies)
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Storage**: AWS S3 (optional, via django-storages)

## Architecture

### Django Apps

- **`babybuddy`** - Root application: authentication, user management, site settings, middleware
- **`core`** - Main data models: Child, Sleep, Feeding, DiaperChange, TummyTime, Pumping, Weight, Height, HeadCircumference, BMI, Note, Timer
- **`api`** - Django REST Framework ViewSets for all core models (namespace: `api`)
- **`dashboard`** - Dashboard cards and widgets (namespace: `dashboard`)
- **`reports`** - Charts and analytics via Plotly (namespace: `reports`)

### URL Structure

- `/admin/` - Django admin
- `/api/` - REST API endpoints
- `/core/` - Core model views (children, sleep, feeding, etc.)
- `/dashboard/` - Dashboard views
- `/reports/` - Report/chart views
- `/user/` - User settings, password, device management
- `/login/`, `/logout/` - Authentication

### Key Settings

- `BABY_BUDDY["ALLOW_UPLOADS"]` - Toggle user file uploads
- `BABY_BUDDY["READ_ONLY_GROUP_NAME"]` - Group name for read-only access
- `ENABLE_HOME_ASSISTANT_SUPPORT` - Home Assistant ingress compatibility

## Common Commands

```bash
# Install dependencies
npm install
pipenv install --dev

# Development server
gulp                    # or: pipenv run python manage.py runserver
gulp runserver          # Django dev server via Pipenv

# Build static assets
gulp build              # Build JS, CSS, fonts, images
gulp scripts            # Build JS only
gulp styles             # Build CSS only
gulp extras             # Copy fonts, logos, images

# Linting
gulp lint               # Python (Black, djlint), JS (Prettier), SCSS (Stylelint)
gulp format             # Auto-fix formatting

# Testing
gulp test               # Run all tests (parallel, excludes "isolate" tag)
gulp coverage           # Run tests with coverage reporting
pipenv run python manage.py test --settings=babybuddy.settings.test  # Direct

# Django management
gulp makemigrations     # Create migrations
gulp migrate            # Apply migrations
gulp collectstatic      # Collect static files
gulp fake               # Populate with fake data for testing
gulp reset              # Reset database

# Documentation
gulp docs:build         # Build MkDocs
gulp docs:watch         # Serve docs locally
```

## Running a Single Test

```bash
pipenv run python manage.py test --settings=babybuddy.settings.test core.tests.SomeTestCase.test_method
```

## Frontend Asset Pipeline

- Source files in `*/static_src/` (JS in `*/static_src/js/`, SCSS in `*/static_src/scss/`)
- Built files in `*/static/` (served by Django)
- Gulp `build` task compiles SCSS to CSS, bundles JS, copies static extras
- Vendor JS (jQuery, Bootstrap, Popper, Masonry, Plotly) is bundled separately

## API

The REST API uses DRF ViewSets under `/api/`. Default pagination is 100 items. Authentication supports both session (browser) and token authentication. The API follows Django's standard model permissions.

## i18n

25 languages supported. Locale files in `locale/`. Use `makemessages`/`compilemessages` gulp tasks for translation updates.
