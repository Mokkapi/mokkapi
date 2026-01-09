# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mokkapi is a mock API server platform that allows developers to create, configure, and manage mock API endpoints with customizable responses, authentication profiles, and HTTP method handling.

**Tech Stack:**
- Backend: Python 3.13+, Django 5.1.6, Django REST Framework
- Frontend: React 19, TypeScript, Vite, Tailwind CSS
- Database: PostgreSQL 17 (production) / SQLite (development)
- Deployment: Docker + Docker Compose, Gunicorn, Nginx

## Common Commands

### Frontend Development
```bash
npm run dev          # Start Vite dev server with hot reload
npm run build        # Type check + production build
npm run type-check   # TypeScript type checking only
```

### Backend Development
```bash
source env/bin/activate         # Activate virtual environment (required first)
python manage.py runserver      # Django development server
python manage.py migrate        # Apply database migrations
python manage.py createsuperuser
```

### Testing
```bash
source env/bin/activate         # Activate virtual environment (required first)
python manage.py test core      # Run Django unit tests
python manage.py test core.tests.test_models  # Run specific test module
python manage.py behave         # Run BDD tests (Behave)
```

**Note:** Tests require `SECRET_KEY` to be set. The project uses environment variables loaded from `.env.dev`. If you see `SECRET_KEY setting must not be empty` errors, ensure the environment file is loaded or set `SECRET_KEY` directly.

### Docker
```bash
docker-compose up               # Start full stack (Django + PostgreSQL + Nginx)
docker-compose build            # Rebuild images
```

## Architecture

```
Frontend (React/TypeScript) → Django REST API (ViewSets) → Django ORM → PostgreSQL
                                    ↓
                        Mock Response Serving (serve_mock_response view)
```

### Key Data Flow
1. Users authenticate via Django session auth
2. Authenticated users manage MockEndpoints via REST API at `/_mokkapi_api_/`
3. Requests to `/api/*` paths are intercepted and return configured mock responses
4. React frontend at `/_mokkapi_api_/app/` provides UI for endpoint management

### Core Models (core/models.py)
- **AuthenticationProfile** - API Key or Basic Auth credentials for mock endpoints
- **MockEndpoint** - Represents a mock API path with optional authentication
- **ResponseHandler** - Maps HTTP method to response (status, headers, body) for an endpoint

### Permission Model
- **UserTrackedModel** base class tracks `creator`, `owner`, `created_at`, `updated_at`
- **IsOwnerOrAdmin** permission ensures users can only modify their own resources

## Key Directories

```
mokkapi/           # Django project config (settings, urls)
core/              # Main app - models, views, serializers, BDD features
  tests/           # Unit tests organized by functionality
user_management/   # Custom user model, auth backends, middleware
assets/            # Frontend source (React components, services, hooks)
  js/components/   # React components
  js/services/     # API client (api.ts)
  js/modules/      # Utilities (resourceController, apiClient)
templates/         # Django HTML templates
static/            # Built frontend assets (Vite output)
env/               # Python virtual environment
```

## Test Organization

Tests are organized in `core/tests/` by functionality:

| File | Description |
|------|-------------|
| `test_models.py` | Model validation and behavior |
| `test_http_verbs.py` | HTTP verb handling (GET, POST, PUT, etc.) |
| `test_handlers.py` | ResponseHandler CRUD operations |
| `test_authentication.py` | Auth profiles and endpoint authentication |
| `test_endpoints.py` | MockEndpoint CRUD, path handling |
| `test_responses.py` | Response content types, encoding |
| `test_api.py` | DRF serializers, API response formats |
| `test_ownership.py` | Multi-tenant isolation |
| `test_concurrency.py` | Concurrent access, state management |
| `test_audit_log.py` | Audit logging (skipped - model not yet implemented) |

## Frontend Patterns

- Entry point: `assets/js/react-app.tsx`
- API communication via `assets/js/services/api.ts` (ApiClient class)
- CSRF token handling in `assets/js/utils/csrf.ts`
- Vite config builds from `assets/` root directory
- React Router with basename `/_mokkapi_api_/app`

## Backend Patterns

- ViewSets in `core/views.py` handle CRUD operations
- `serve_mock_response` view (same file) handles mock endpoint serving
- Serializers have separate create vs. retrieve versions (e.g., `MockEndpointCreateSerializer`)
- Custom `CurrentUserMiddleware` in `user_management/middleware.py`

## Environment Variables

Key variables (see `.env.dev` for development):
- `DEBUG`, `SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`
- `DIGITAL_OCEAN_SPACES_*` for S3 storage integration
