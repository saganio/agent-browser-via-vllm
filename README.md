# Browser Test Platform

Enterprise-grade AI-powered browser test automation platform with multi-tenant support, OIDC authentication, and real-time test execution.

## Features

- **Multi-Tenant Architecture**: Organization-based isolation with role-based access control (Admin, Developer, Viewer)
- **OIDC Authentication**: Support for custom OIDC providers for enterprise SSO
- **AI-Powered Testing**: Natural language commands powered by vLLM with tool-calling capabilities
- **Real-Time Execution**: WebSocket-based live test execution with streaming results
- **Scheduled Tests**: Cron-based test scheduling with APScheduler
- **Parallel Execution**: Celery workers with Redis for concurrent test runs
- **Notifications**: Email, Slack, Discord, and Webhook notifications
- **Analytics Dashboard**: Comprehensive reports and charts with Recharts
- **Modern UI**: Built with Takeoff UI components and Tailwind CSS

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │     │   Backend       │     │   Workers       │
│   (React +      │────▶│   (FastAPI)     │────▶│   (Celery)      │
│   Takeoff UI)   │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   PostgreSQL    │     │   Redis         │
                        │   (Data Store)  │     │   (Task Queue)  │
                        └─────────────────┘     └─────────────────┘
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+
- agent-browser CLI (optional, for actual browser automation)

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Start Celery Workers (for parallel execution)

```bash
cd backend
source venv/bin/activate

# Start worker
celery -A app.workers.celery_app worker --loglevel=info -Q browser_tests
```

## Environment Variables

Create a `.env` file in the backend directory:

```env
# Application
APP_NAME=Browser Test Platform
DEBUG=true
SECRET_KEY=your-super-secret-key-change-in-production

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/browser_tests

# Redis
REDIS_URL=redis://localhost:6379/0

# OIDC (optional)
OIDC_DISCOVERY_URL=https://your-provider/.well-known/openid-configuration
OIDC_CLIENT_ID=browser-test-platform
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=http://localhost:8080/api/auth/callback

# JWT
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Storage (local by default)
USE_LOCAL_STORAGE=true
LOCAL_STORAGE_PATH=./storage

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user
- `GET /api/auth/oidc/login` - Initiate OIDC login
- `GET /api/auth/oidc/callback` - OIDC callback

### Projects
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `GET /api/projects/{id}` - Get project
- `PATCH /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project
- `GET /api/projects/{id}/stats` - Get project statistics

### Tests
- `POST /api/tests/execute` - Create test run
- `GET /api/tests` - List test runs
- `GET /api/tests/{id}` - Get test run details
- `POST /api/tests/{id}/cancel` - Cancel test run
- `WS /ws/tests/{id}/execute` - WebSocket for real-time execution

### Schedules
- `GET /api/tests/schedules` - List schedules
- `POST /api/tests/schedules` - Create schedule
- `PATCH /api/tests/schedules/{id}` - Update schedule
- `DELETE /api/tests/schedules/{id}` - Delete schedule

### Notifications
- `GET /api/notifications/channels` - List channels
- `POST /api/notifications/channels` - Create channel
- `PATCH /api/notifications/channels/{id}` - Update channel
- `DELETE /api/notifications/channels/{id}` - Delete channel
- `POST /api/notifications/channels/{id}/test` - Test channel

## Project Structure

```
browser-test-platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Settings
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── websocket.py         # WebSocket handlers
│   │   ├── auth/                # Authentication
│   │   │   ├── models.py        # User, Organization models
│   │   │   ├── router.py        # Auth endpoints
│   │   │   ├── oidc.py          # OIDC client
│   │   │   ├── jwt.py           # JWT handling
│   │   │   └── dependencies.py  # Auth dependencies
│   │   ├── projects/            # Project management
│   │   ├── tests/               # Test execution
│   │   │   ├── orchestrator.py  # AI agent orchestrator
│   │   │   └── scheduler.py     # APScheduler
│   │   ├── workers/             # Celery workers
│   │   └── notifications/       # Notification channels
│   ├── alembic/                 # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app component
│   │   ├── api/                 # API client
│   │   ├── auth/                # Auth context & guards
│   │   ├── components/          # UI components
│   │   ├── pages/               # Page components
│   │   ├── store/               # Zustand stores
│   │   └── types/               # TypeScript types
│   └── package.json
└── README.md
```

## User Roles

| Role | Permissions |
|------|-------------|
| Admin | Full access, manage users, settings, delete projects |
| Developer | Create/edit projects, run tests, manage schedules |
| Viewer | View projects, tests, and reports |

## vLLM Configuration

Each project can have its own vLLM configuration:

```json
{
  "api_url": "http://localhost:8000",
  "model_name": "meta-llama/Llama-3.1-8B-Instruct",
  "temperature": 0.7,
  "max_tokens": 2048,
  "api_key": "optional-api-key"
}
```

## Notification Channels

### Slack
```json
{
  "webhook_url": "https://hooks.slack.com/services/...",
  "channel": "#alerts"
}
```

### Email
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "user@example.com",
  "password": "app-password",
  "from_email": "noreply@example.com",
  "to_emails": ["team@example.com"]
}
```

### Webhook
```json
{
  "url": "https://api.example.com/webhook",
  "auth_token": "Bearer token"
}
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Production Deployment

1. Set `DEBUG=false` in environment
2. Use a proper `SECRET_KEY`
3. Configure PostgreSQL and Redis for production
4. Set up reverse proxy (nginx/traefik)
5. Enable HTTPS
6. Configure proper CORS origins
7. Set up monitoring and logging

## License

MIT
