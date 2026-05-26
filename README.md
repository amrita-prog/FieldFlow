# FieldFlow — Field Force Management System

A backend API for managing field agents, tasks, visits, and reporting — built with Django REST Framework.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.13 |
| **Framework** | Django 6.0, Django REST Framework 3.17 |
| **Auth** | SimpleJWT (access + refresh tokens, blacklist on logout) |
| **Database** | SQLite (dev) — swappable to PostgreSQL for production |
| **Filters** | django-filter, DRF SearchFilter, OrderingFilter |
| **CORS** | django-cors-headers |

---

## Project Overview

FieldFlow manages a hierarchy of roles, each with scoped access to data:

```
Admin
  └── Regional Manager  (region-scoped)
        └── Team Lead   (team-scoped)
              └── Field Agent  (own data only)
Auditor  (read-only across all data)
```

### Modules

| Module | Description |
|---|---|
| **Auth** | JWT login/logout, token refresh, current user profile |
| **Users** | Admin-managed user CRUD with soft-delete |
| **Tasks** | Task lifecycle: create → assign → in_progress → completed |
| **Visits** | Field visit tracking: scheduled → in_progress → completed |
| **AI Service** | Mock AI analysis of visit notes (risk detection + summaries) |
| **Reports** | SQL-powered reports scoped by role |
| **Logs** | Immutable audit trail of all system events |

---

## Project Structure

```
FieldFlow/
├── backend/                  # Django settings, root URLs, WSGI
│   ├── settings.py
│   ├── urls.py
│   ├── exceptions.py         # Custom DRF error format
│   └── wsgi.py
│
├── accounts/                 # Auth, users, roles, permissions
│   ├── models.py             # User, Role, Region, Team, ModulePermission, EmployeeProfile
│   ├── serializers.py
│   ├── views.py              # LoginView, LogoutView, MeView, UserViewSet
│   ├── permissions.py        # HasModulePermission, IsOwnerOrInScope
│   └── management/commands/seed.py
│
├── tasks/                    # Task management
│   ├── models.py             # Task with state machine
│   ├── mixins.py             # ScopedQuerysetMixin (reusable)
│   ├── filters.py
│   ├── serializers.py
│   └── views.py              # TaskViewSet + assign + update_status
│
├── visits/                   # Visit tracking
│   ├── models.py             # Visit, AIOutput
│   ├── serializers.py
│   ├── filters.py
│   └── views.py              # VisitViewSet + start + complete + notes + ai-output
│
├── ai_service/               # Mock AI service
│   └── service.py            # MockAIService (swap-in for real LLM)
│
├── reports/                  # Reporting
│   ├── queries.py            # Raw SQL + ORM report functions
│   └── views.py              # 5 report endpoints
│
├── logs/                     # Activity audit trail
│   ├── models.py             # ActivityLog
│   ├── utils.py              # log_activity() helper
│   └── views.py              # ActivityLogViewSet (read-only)
│
├── scripts/
│   ├── seed_sample_data.py   # Sample tasks/visits for testing
│   └── test_reports.py       # Automated report verification
│
├── test.http                 # REST Client test file (57 test cases)
├── requirements.txt
├── .env.example
└── manage.py
```

---

## Setup Instructions

### Prerequisites
- Python 3.10+ (tested on 3.13)
- pip

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd FieldFlow
```

### 2. Create and activate virtual environment

```bash
# Windows
python -m venv env
env\Scripts\activate

# macOS / Linux
python -m venv env
source env/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
# Copy the example env file (no changes needed for SQLite dev setup)
cp .env.example .env
```

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. Seed the database

```bash
python manage.py seed
```

This creates:
- 5 roles with full module permission matrix
- 2 regions (North Zone, South Zone)
- 3 teams (Alpha, Beta, Gamma)
- 12 users (see credentials below)

### 7. (Optional) Add sample task & visit data

```bash
python scripts/seed_sample_data.py
```

### 8. Start the development server

```bash
python manage.py runserver
```

API is now running at: **`http://127.0.0.1:8000/api/`**

---

## Seeded Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@fieldflow.com | Admin@123 |
| Regional Manager | rm.north@fieldflow.com | Pass@123 |
| Regional Manager | rm.south@fieldflow.com | Pass@123 |
| Team Lead | tl.alpha@fieldflow.com | Pass@123 |
| Team Lead | tl.beta@fieldflow.com | Pass@123 |
| Team Lead | tl.gamma@fieldflow.com | Pass@123 |
| Field Agent | agent1@fieldflow.com | Pass@123 |
| Field Agent | agent2@fieldflow.com | Pass@123 |
| Field Agent | agent3@fieldflow.com | Pass@123 |
| Field Agent | agent4@fieldflow.com | Pass@123 |
| Field Agent | agent5@fieldflow.com | Pass@123 |
| Auditor | auditor@fieldflow.com | Pass@123 |

---

## API Reference

Base URL: `http://127.0.0.1:8000/api`

All endpoints (except `/auth/login/`) require:
```
Authorization: Bearer <access_token>
```

### Auth

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login/` | Public | Login, returns JWT pair + user profile |
| POST | `/auth/logout/` | Required | Blacklist refresh token |
| POST | `/auth/token/refresh/` | Public | Get new access token |
| GET | `/auth/me/` | Required | Current user profile + permissions |

### Users (Admin only)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/users/` | List all users (filter: `?role=`, `?is_active=`) |
| POST | `/users/` | Create new user |
| GET | `/users/{id}/` | User detail |
| PATCH | `/users/{id}/` | Update user |
| DELETE | `/users/{id}/` | Soft-deactivate (sets `is_active=False`) |

### Tasks

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/tasks/` | All roles | List (scope-filtered) |
| POST | `/tasks/` | Admin, RM, TL | Create task |
| GET | `/tasks/{id}/` | All roles | Task detail |
| PATCH | `/tasks/{id}/` | Admin, RM, TL | Update task fields |
| DELETE | `/tasks/{id}/` | Admin only | Soft-cancel task |
| POST | `/tasks/{id}/assign/` | Admin, RM, TL | Assign to Field Agent |
| PATCH | `/tasks/{id}/status/` | All roles | Update status (state machine) |

**Filters**: `?status=`, `?priority=`, `?assigned_to=`, `?region=`, `?team=`, `?due_date=`, `?overdue=true`  
**Search**: `?search=` (title + description)  
**Ordering**: `?ordering=due_date`, `?ordering=-priority`

**Task Status Machine**:
```
pending → in_progress → completed
    ↓            ↓
 cancelled    cancelled
```

### Visits

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/visits/` | All roles | List (scope-filtered) |
| POST | `/visits/` | All roles | Create visit |
| GET | `/visits/{id}/` | All roles | Visit detail + AI output |
| POST | `/visits/{id}/start/` | Agent/Admin | Start visit |
| POST | `/visits/{id}/complete/` | Agent/Admin | Complete visit (requires outcome) |
| PATCH | `/visits/{id}/notes/` | Agent/Admin | Add/update notes → triggers AI |
| GET | `/visits/{id}/ai-output/` | All roles | Fetch AI analysis |

**Filters**: `?status=`, `?outcome=`, `?agent=`, `?risk_flag=`, `?completed_after=`, `?completed_before=`

**Visit Status Machine**:
```
scheduled → in_progress → completed
                ↓
            cancelled
```

### Reports

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/reports/dashboard-summary/` | All roles | Scoped task + visit counts |
| GET | `/reports/pending-tasks/` | Admin, RM, TL, Auditor | Pending tasks by region/team |
| GET | `/reports/agent-performance/` | Admin, RM, TL, Auditor | Avg task completion time per agent |
| GET | `/reports/recent-visits/` | Admin, RM, TL, Auditor | Visits in last N days (`?days=7`) |
| GET | `/reports/task-distribution/` | Admin, RM, TL, Auditor | Status breakdown by manager |

### Activity Logs

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/logs/` | Admin, RM, TL, Auditor | List logs (scoped) |
| GET | `/logs/{id}/` | Admin, RM, TL, Auditor | Single log entry |

**Filters**: `?action=`, `?actor_id=`, `?target_type=`, `?from=YYYY-MM-DD`, `?to=YYYY-MM-DD`

---

## Access Control Matrix

| Module | Admin | Regional Manager | Team Lead | Field Agent | Auditor |
|---|---|---|---|---|---|
| **Users** | Full CRUD | Read (region) | Read (team) | None | Read (all) |
| **Tasks** | Full CRUD | Create/Read/Update (region) | Create/Read/Update (team) | Read/Update own | Read (all) |
| **Visits** | Full CRUD | Read (region) | Read (team) | Create/Read/Update own | Read (all) |
| **Reports** | All | Region-scoped | Team-scoped | Dashboard only | All |
| **Logs** | All | Region-scoped | Team-scoped | None | All |

### Scope Definitions

| Scope | Meaning |
|---|---|
| `all` | Can see every record regardless of region/team |
| `region` | Can only see records in their assigned region |
| `team` | Can only see records in their assigned team |
| `own` | Can only see records assigned to / created by themselves |

---

## Mock AI Service

The `ai_service/service.py` module contains `MockAIService` — a deterministic, keyword-based AI simulator.

**How it works:**
1. Scans visit notes (case-insensitive) for risk keywords
2. Classifies as `high`, `medium`, or `low` risk
3. Generates a summary and follow-up recommendation

**High risk keywords**: `refused`, `hostile`, `emergency`, `damaged`, `unsafe`, `hazard`, `escalate`, `theft`, etc.  
**Medium risk keywords**: `delayed`, `issue`, `complaint`, `incomplete`, `follow up`, etc.

**Swap for a real LLM**: Replace `MockAIService.generate_output()` in `ai_service/service.py` with an API call to OpenAI, Gemini, or any other provider. Zero changes required in visit views.

---

## Error Response Format

All API errors return a consistent JSON shape:

```json
{
  "error": true,
  "code": "PERMISSION_DENIED",
  "message": "Field Agents do not have access to reports.",
  "details": {}
}
```

Common codes: `UNAUTHORIZED`, `PERMISSION_DENIED`, `NOT_FOUND`, `BAD_REQUEST`, `INVALID_STATE`, `VALIDATION_FAILED`

---

## Testing

Open `test.http` in VS Code with the [REST Client extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client).

The file contains **57 test cases** across all phases:
- **Phase 1** (1.1–1.15): Auth, user management
- **Phase 2** (2.1–2.18): Task CRUD, assign, status updates
- **Phase 3** (3.1–3.21): Visit lifecycle, AI output
- **Phase 4** (4.1–4.12): All report endpoints
- **Phase 5** (5.1–5.15): Activity log filtering

**Quick start:**
1. Send request `1.1` (Login as Admin)
2. Copy `access` token from response
3. Paste it into `@accessToken = ` at the top of the file
4. Run all other requests

---

## Assumptions & Tradeoffs

| Decision | Rationale |
|---|---|
| SQLite for dev | Zero setup required. Switch to PostgreSQL by changing `DATABASES` in settings |
| Email as login field | More natural for professional users than username-based login |
| Soft delete for users | Preserves audit trail and task assignment history |
| ModulePermission in DB | Dynamic — permissions can be changed without code deployment |
| Deterministic mock AI | Zero cost, zero latency, reproducible for testing. Swap via `service.py` only |
| UUID PKs everywhere | Prevents ID enumeration attacks and allows future distributed systems |
| Token blacklist | Enables proper logout (stateless JWT limitation overcome) |
| Scoped querysets | Applied at `get_queryset()` level — data leakage is impossible even with direct ID access |
| Raw SQL for reports | Demonstrates SQL proficiency and allows fine-grained aggregation control |

---

## Running with PostgreSQL (Production)

1. Install PostgreSQL and create a database:
   ```sql
   CREATE DATABASE fieldflow_db;
   CREATE USER fieldflow WITH PASSWORD 'yourpassword';
   GRANT ALL PRIVILEGES ON DATABASE fieldflow_db TO fieldflow;
   ```

2. Update `.env`:
   ```
   DATABASE_URL=postgresql://fieldflow:yourpassword@localhost:5432/fieldflow_db
   ```

3. Update `backend/settings.py` to read from `DATABASE_URL` using `django-environ`.

4. Run migrations and seed as normal.
