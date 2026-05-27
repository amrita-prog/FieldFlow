# FieldFlow API Integration — Complete Reference

> **Base URL**: `http://127.0.0.1:8000/api`  
> **Content-Type**: `application/json` (all requests)  
> **Authentication**: `Authorization: Bearer <access_token>` (required on all endpoints except login & token refresh)

---

## Global Error Format

Every error from the API returns this exact shape — no exceptions.

```json
{
  "error": true,
  "code": "PERMISSION_DENIED",
  "message": "Field Agents do not have access to reports.",
  "details": {}
}
```

| Field | What it means |
|---|---|
| `error` | Always `true` on error responses |
| `code` | Machine-readable error code. Use for programmatic handling |
| `message` | Human-readable string. Safe to show directly to the user |
| `details` | Field-level validation errors (only on 400 validation failures) |

**Common `code` values:**

| Code | HTTP Status | When it happens |
|---|---|---|
| `UNAUTHORIZED` | 401 | No/invalid/expired token |
| `PERMISSION_DENIED` | 403 | Role doesn't allow this action |
| `NOT_FOUND` | 404 | Resource doesn't exist in user's scope |
| `BAD_REQUEST` | 400 | Missing or malformed request body |
| `VALIDATION_FAILED` | 400 | Field-level errors (see `details`) |
| `INVALID_STATE` | 400 | State machine violation (e.g. completing a visit that hasn't started) |

---

## Paginated List Format

All list endpoints (`/tasks/`, `/visits/`, `/logs/`, `/users/`) return:

```json
{
  "count": 47,
  "next": "http://127.0.0.1:8000/api/tasks/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

| Field | What it means |
|---|---|
| `count` | Total records matching the query (all pages combined) |
| `next` | Full URL to next page, or `null` if on last page |
| `previous` | Full URL to previous page, or `null` if on first page |
| `results` | Array of objects for this page (max 20 per page) |

**How to paginate:** Append `?page=2`, `?page=3` etc. to the URL.

---

---

# MODULE 1 — Auth & Users

---

## 1.1 Login

**`POST /auth/login/`** — Public (no token required)

Use this first. It returns both JWT tokens and the complete user profile in one call.

**Request Body:**
```json
{
  "email": "tl.alpha@fieldflow.com",
  "password": "Pass@123"
}
```

**Success Response (200):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "3f2a1b8c-7e4d-4c09-a1b2-123456789abc",
    "username": "tl_alpha",
    "email": "tl.alpha@fieldflow.com",
    "first_name": "Alpha",
    "last_name": "Lead",
    "full_name": "Alpha Lead",
    "is_active": true,
    "date_joined": "2026-05-20T12:00:00Z",
    "last_login": "2026-05-27T07:30:00Z",
    "role": {
      "id": 3,
      "name": "Team Lead",
      "description": "Manages a specific team within a region"
    },
    "region": {
      "id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
      "name": "North Zone"
    },
    "team": {
      "id": "c1d2e3f4-a5b6-7890-cdef-1234567890ab",
      "name": "Alpha Team",
      "region": {
        "id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
        "name": "North Zone"
      }
    },
    "profile": {
      "phone": "+91-9876543210",
      "employee_code": "EMP3F2A1B",
      "joining_date": "2025-01-15"
    },
    "permissions": [
      {
        "module": "tasks",
        "can_create": true,
        "can_read": true,
        "can_update": true,
        "can_delete": false,
        "scope": "team"
      },
      {
        "module": "visits",
        "can_create": false,
        "can_read": true,
        "can_update": false,
        "can_delete": false,
        "scope": "team"
      },
      {
        "module": "reports",
        "can_create": false,
        "can_read": true,
        "can_update": false,
        "can_delete": false,
        "scope": "team"
      }
    ]
  }
}
```

**How to use it:**
1. Save `access` token — send it as `Authorization: Bearer <access>` on every subsequent request
2. Save `refresh` token — use it to get new access tokens when they expire (30 min)
3. Save `user.role.name` — use it to control which pages/menus the user sees
4. Save `user.permissions` array — use it to show/hide individual buttons like "Create Task", "Delete", etc.

**Error Responses:**
```json
// 400 — Wrong password or email
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Invalid email or password.",
  "details": {}
}

// 400 — Deactivated account
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "This account has been deactivated.",
  "details": {}
}
```

---

## 1.2 Refresh Token

**`POST /auth/token/refresh/`** — Public (no token required)

Call this when any API returns `401 Unauthorized`. The access token expires after 30 minutes.

**Request Body:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...(new token)...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...(new refresh token)..."
}
```

> ⚠️ **Important:** Both the `access` AND `refresh` tokens are rotated each time. Save the new `refresh` token too — the old one is invalidated.

**Error Responses:**
```json
// 401 — Refresh token expired or blacklisted (user must log in again)
{
  "error": true,
  "code": "UNAUTHORIZED",
  "message": "Token is invalid or expired.",
  "details": {}
}
```

**How to use it:** Set up an Axios response interceptor. Catch `401`, automatically call this endpoint, update saved tokens, and retry the original failed request — invisible to the user.

---

## 1.3 Logout

**`POST /auth/logout/`** — Requires token

**Request Body:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "message": "Logged out successfully."
}
```

**Error Responses:**
```json
// 400 — No refresh token sent
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Refresh token is required.",
  "details": {}
}

// 400 — Token already used/invalid
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Token is invalid or already blacklisted.",
  "details": {}
}
```

**How to use it:** On logout button click → call this → on success, clear localStorage, clear Axios auth header, redirect to login.

---

## 1.4 Get Current User (Me)

**`GET /auth/me/`** — Requires token

Returns the same shape as the `user` object inside the login response.

**Success Response (200):** *(same structure as `user` inside login response — see 1.1)*

**How to use it:**
- Call on app startup (if a token exists in localStorage) to verify the token is valid and restore the user session
- If this returns `401`, redirect to login

---

## 1.5 List Users

**`GET /users/`** — Admin only

**Query Params:**
| Param | Example | Purpose |
|---|---|---|
| `role` | `?role=Field Agent` | Filter by role name |
| `is_active` | `?is_active=true` | Filter active/inactive |
| `page` | `?page=2` | Pagination |

**Success Response (200):** Paginated list.
```json
{
  "count": 12,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "49407ea5-894a-4cc8-a639-8355513daf96",
      "username": "admin",
      "email": "admin@fieldflow.com",
      "full_name": "Admin User",
      "role_name": "Admin"
    },
    {
      "id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5",
      "username": "agent1",
      "email": "agent1@fieldflow.com",
      "full_name": "Field Agent One",
      "role_name": "Field Agent"
    }
  ]
}
```

> Note: The list view returns the **brief** user shape (id, username, email, full_name, role_name). Use `GET /users/{id}/` for the full profile.

---

## 1.6 Get Single User

**`GET /users/{id}/`** — Admin only

**Success Response (200):** Full user profile (same shape as login `user` object — see 1.1).

---

## 1.7 Create User

**`POST /users/`** — Admin only

**Request Body:**
```json
{
  "username": "new_agent",
  "email": "new.agent@fieldflow.com",
  "password": "SecurePass@123",
  "first_name": "Rajesh",
  "last_name": "Kumar",
  "role_id": 4,
  "region_id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
  "team_id": "c1d2e3f4-a5b6-7890-cdef-1234567890ab"
}
```

| Field | Required | Notes |
|---|---|---|
| `username` | ✅ | Must be unique |
| `email` | ✅ | Must be unique |
| `password` | ✅ | Min 6 characters |
| `role_id` | ✅ | Integer: 1=Admin, 2=RM, 3=TL, 4=Field Agent, 5=Auditor |
| `region_id` | Optional | UUID of region |
| `team_id` | Optional | UUID of team |

**Success Response (201):** Full user detail object (same shape as login `user` — see 1.1).

**Error Responses:**
```json
// 400 — Duplicate email or username
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Validation failed.",
  "details": {
    "email": ["user with this email already exists."]
  }
}
```

---

## 1.8 Update User

**`PATCH /users/{id}/`** — Admin only

Send only the fields you want to update. All fields are optional.

**Request Body:**
```json
{
  "first_name": "Rajesh",
  "last_name": "Sharma",
  "is_active": true,
  "role_id": 3,
  "region_id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
  "team_id": null
}
```

**Success Response (200):** Full user detail object.

---

## 1.9 Deactivate User (Soft Delete)

**`DELETE /users/{id}/`** — Admin only

Does **not** permanently delete. Sets `is_active = false`. The user's task history and visit records are preserved.

**Success Response (200):**
```json
{
  "message": "User agent1@fieldflow.com has been deactivated."
}
```

**Error Responses:**
```json
// 400 — Admin trying to delete their own account
{
  "error": true,
  "code": "SELF_DELETE",
  "message": "You cannot deactivate your own account.",
  "details": {}
}
```

---

---

# MODULE 2 — Tasks

---

## 2.1 List Tasks

**`GET /tasks/`** — All roles

> The backend **automatically scopes** results. Admin sees all, RM sees their region, TL sees their team, Field Agent sees only their own assigned tasks. You don't need to pass any user ID.

**Query Params:**
| Param | Example | Purpose |
|---|---|---|
| `status` | `?status=pending` | Filter: pending, in_progress, completed, cancelled |
| `priority` | `?priority=high` | Filter: low, medium, high, critical |
| `assigned_to` | `?assigned_to=<uuid>` | Filter by specific agent UUID |
| `region` | `?region=<uuid>` | Filter by region UUID |
| `team` | `?team=<uuid>` | Filter by team UUID |
| `due_date` | `?due_date=2026-06-01` | Exact due date |
| `search` | `?search=transformer` | Search in title and description |
| `ordering` | `?ordering=-due_date` | Sort. Prefix `-` for descending |
| `page` | `?page=2` | Pagination |

**Success Response (200):**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "2a48155a-f635-41e0-bee6-fd9508b04493",
      "title": "Inspect Main Transformer T-12",
      "status": "pending",
      "priority": "high",
      "assigned_to": {
        "id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5",
        "username": "agent1",
        "email": "agent1@fieldflow.com",
        "full_name": "Field Agent One",
        "role_name": "Field Agent"
      },
      "created_by": {
        "id": "3f2a1b8c-7e4d-4c09-a1b2-123456789abc",
        "username": "tl_alpha",
        "email": "tl.alpha@fieldflow.com",
        "full_name": "Alpha Lead",
        "role_name": "Team Lead"
      },
      "region_name": "North Zone",
      "team_name": "Alpha Team",
      "due_date": "2026-06-15",
      "created_at": "2026-05-27T07:00:00Z",
      "updated_at": "2026-05-27T07:00:00Z"
    }
  ]
}
```

---

## 2.2 Get Task Detail

**`GET /tasks/{id}/`** — All roles (scoped)

**Success Response (200):**
```json
{
  "id": "2a48155a-f635-41e0-bee6-fd9508b04493",
  "title": "Inspect Main Transformer T-12",
  "description": "Perform a full safety inspection on transformer unit T-12 in sector 5.",
  "status": "pending",
  "priority": "high",
  "created_by": {
    "id": "3f2a1b8c-7e4d-4c09-a1b2-123456789abc",
    "username": "tl_alpha",
    "email": "tl.alpha@fieldflow.com",
    "full_name": "Alpha Lead",
    "role_name": "Team Lead"
  },
  "assigned_to": {
    "id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5",
    "username": "agent1",
    "email": "agent1@fieldflow.com",
    "full_name": "Field Agent One",
    "role_name": "Field Agent"
  },
  "region": {
    "id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
    "name": "North Zone"
  },
  "team": {
    "id": "c1d2e3f4-a5b6-7890-cdef-1234567890ab",
    "name": "Alpha Team",
    "region": {
      "id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
      "name": "North Zone"
    }
  },
  "due_date": "2026-06-15",
  "created_at": "2026-05-27T07:00:00Z",
  "updated_at": "2026-05-27T07:00:00Z"
}
```

**Error Responses:**
```json
// 404 — Task not found, or outside user's scope
{
  "error": true,
  "code": "NOT_FOUND",
  "message": "No Task matches the given query.",
  "details": {}
}
```

---

## 2.3 Create Task

**`POST /tasks/`** — Admin, Regional Manager, Team Lead

**Request Body:**
```json
{
  "title": "Replace Faulty Meters - Sector 7",
  "description": "Customer complaint regarding inaccurate meter readings. Inspection and replacement needed.",
  "priority": "medium",
  "due_date": "2026-07-10",
  "assigned_to_id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5",
  "region_id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
  "team_id": "c1d2e3f4-a5b6-7890-cdef-1234567890ab"
}
```

| Field | Required | Notes |
|---|---|---|
| `title` | ✅ | Task name |
| `priority` | ✅ | low / medium / high / critical |
| `description` | Optional | |
| `due_date` | Optional | Must not be a past date (YYYY-MM-DD format) |
| `assigned_to_id` | Optional | UUID. Must be a Field Agent |
| `region_id` | Optional | UUID. Auto-filled from the creator's region if not provided |
| `team_id` | Optional | UUID. Auto-filled from the creator's team if not provided |

**Success Response (201):** Full `TaskDetail` object (see 2.2).

**Error Responses:**
```json
// 400 — Assigning to non-Field-Agent
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Validation failed.",
  "details": {
    "assigned_to_id": [
      "Tasks can only be assigned to Field Agents. tl.alpha@fieldflow.com has role: Team Lead."
    ]
  }
}

// 400 — Past due date
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Validation failed.",
  "details": {
    "due_date": ["Due date cannot be in the past."]
  }
}
```

---

## 2.4 Update Task

**`PATCH /tasks/{id}/`** — Admin, Regional Manager, Team Lead

Send only the fields to update. You cannot change `status` here — use `2.5` for that.

**Request Body:**
```json
{
  "title": "Updated Title",
  "description": "Updated description.",
  "priority": "critical",
  "due_date": "2026-08-01"
}
```

**Success Response (200):** Full `TaskDetail` object.

---

## 2.5 Update Task Status

**`PATCH /tasks/{id}/status/`** — All roles (state machine enforced)

**Valid Status Transitions:**

| Current Status | Can move to |
|---|---|
| `pending` | `in_progress`, `cancelled` |
| `in_progress` | `completed`, `cancelled` |
| `completed` | *(terminal — no transitions)* |
| `cancelled` | *(terminal — no transitions)* |

**Request Body:**
```json
{
  "status": "in_progress"
}
```

**Success Response (200):** Full `TaskDetail` object with updated status.

**Error Responses:**
```json
// 400 — Invalid transition (e.g. pending → completed)
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Validation failed.",
  "details": {
    "status": [
      "Cannot move task from \"pending\" to \"completed\". Allowed transitions: ['in_progress', 'cancelled']."
    ]
  }
}
```

---

## 2.6 Assign Task to Agent

**`POST /tasks/{id}/assign/`** — Admin, Regional Manager, Team Lead

**Request Body:**
```json
{
  "assigned_to_id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5"
}
```

**Success Response (200):** Full `TaskDetail` object with new `assigned_to`.

**Error Responses:**
```json
// 400 — User is not a Field Agent
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Validation failed.",
  "details": {
    "assigned_to_id": [
      "tl.alpha@fieldflow.com is not a Field Agent (role: Team Lead)."
    ]
  }
}

// 400 — Agent is outside TL's scope
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Validation failed.",
  "details": {
    "non_field_errors": [
      "You can only assign tasks to agents in your team (Alpha Team)."
    ]
  }
}
```

---

## 2.7 Cancel/Delete Task

**`DELETE /tasks/{id}/`** — Admin only

Sets the task status to `cancelled`. Does not remove from DB.

**Success Response (204):** No content.

---

---

# MODULE 3 — Visits & AI

---

## 3.1 List Visits

**`GET /visits/`** — All roles (scoped)

**Query Params:**
| Param | Example | Purpose |
|---|---|---|
| `status` | `?status=in_progress` | scheduled / in_progress / completed / cancelled |
| `outcome` | `?outcome=failed` | successful / failed / partial / pending |
| `agent` | `?agent=<uuid>` | Filter by specific agent |
| `ordering` | `?ordering=-created_at` | Sort field |
| `page` | `?page=1` | Pagination |

**Success Response (200):**
```json
{
  "count": 6,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "657ee852-fb6b-4269-a462-2cf76856f083",
      "agent": {
        "id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5",
        "username": "agent1",
        "email": "agent1@fieldflow.com",
        "full_name": "Field Agent One",
        "role_name": "Field Agent"
      },
      "location": "Sector 12 Main Substation",
      "status": "completed",
      "outcome": "successful",
      "task_title": "Inspect Main Transformer T-12",
      "risk_flag": "low",
      "started_at": "2026-05-27T04:00:00Z",
      "completed_at": "2026-05-27T07:00:00Z",
      "created_at": "2026-05-27T03:50:00Z"
    }
  ]
}
```

---

## 3.2 Get Visit Detail

**`GET /visits/{id}/`** — All roles (scoped)

Returns the complete visit object including the linked task brief and AI output.

**Success Response (200):**
```json
{
  "id": "657ee852-fb6b-4269-a462-2cf76856f083",
  "task": {
    "id": "2a48155a-f635-41e0-bee6-fd9508b04493",
    "title": "Inspect Main Transformer T-12",
    "status": "in_progress",
    "priority": "high"
  },
  "agent": {
    "id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5",
    "username": "agent1",
    "email": "agent1@fieldflow.com",
    "full_name": "Field Agent One",
    "role_name": "Field Agent"
  },
  "location": "Sector 12 Main Substation",
  "status": "completed",
  "outcome": "successful",
  "notes": "Inspection completed. Transformer in good condition.",
  "started_at": "2026-05-27T04:00:00Z",
  "completed_at": "2026-05-27T07:00:00Z",
  "created_at": "2026-05-27T03:50:00Z",
  "updated_at": "2026-05-27T07:05:00Z",
  "ai_output": {
    "summary": "Agent reported a successful inspection at Sector 12 Main Substation. The transformer was found to be in good working condition.",
    "follow_up": "No immediate follow-up required. Schedule routine check in 3 months.",
    "risk_flag": "low",
    "generated_at": "2026-05-27T07:05:30Z"
  }
}
```

> **Note:** `ai_output` is `null` if notes have not been submitted yet.

---

## 3.3 Create Visit

**`POST /visits/`** — All roles

**Request Body:**
```json
{
  "location": "Warehouse Gate 5, Industrial Area",
  "task_id": "2a48155a-f635-41e0-bee6-fd9508b04493"
}
```

| Field | Required | Notes |
|---|---|---|
| `location` | ✅ | Where the visit takes place |
| `task_id` | Optional | UUID of a linked Task |
| `agent_id` | Optional | UUID. Only for Admin/Managers creating a visit on behalf of an agent. Field Agents are auto-set as the agent. |

**Success Response (201):** Full `VisitDetail` object (same as 3.2), with `status: "scheduled"`, `ai_output: null`.

---

## 3.4 Start Visit

**`POST /visits/{id}/start/`** — Field Agent (own visit) or Admin/Manager

Visit must currently be in `scheduled` status.

**Request Body:** `{}` (empty object — no body needed)

**Success Response (200):** Full `VisitDetail` object with:
- `status` changed to `"in_progress"`
- `started_at` set to current server timestamp

**Error Responses:**
```json
// 400 — Already started (double-click prevention)
{
  "error": true,
  "code": "INVALID_STATE",
  "message": "Visit is currently \"in_progress\". Only scheduled visits can be started.",
  "details": {}
}

// 403 — Field Agent trying to start another agent's visit
{
  "error": true,
  "code": "PERMISSION_DENIED",
  "message": "You can only start visits assigned to you.",
  "details": {}
}
```

---

## 3.5 Add Notes (Triggers AI Analysis)

**`PATCH /visits/{id}/notes/`** — Field Agent (own) or Admin/Manager

This is the most important action for Field Agents. Submitting notes automatically triggers the AI risk detection engine. The response includes the AI output.

**Request Body:**
```json
{
  "notes": "Customer refused to allow access to the meter room. Became hostile when asked to comply. There is visible damage to the external fuse box which poses a safety hazard.",
  "outcome": "failed"
}
```

| Field | Required | Notes |
|---|---|---|
| `notes` | ✅ | Min 5 chars, max 5000 chars |
| `outcome` | Optional | successful / failed / partial / pending |

**Success Response (200):** Full `VisitDetail` object. The `ai_output` block is now populated:

```json
{
  "id": "657ee852-fb6b-4269-a462-2cf76856f083",
  "status": "in_progress",
  "notes": "Customer refused to allow access to the meter room...",
  "outcome": "failed",
  "ai_output": {
    "summary": "During the visit to the location, the agent encountered significant resistance. Customer refused entry and showed hostile behavior. External infrastructure damage was noted as a safety concern.",
    "follow_up": "Immediate supervisor escalation required. Do not revisit without security escort. File an incident report.",
    "risk_flag": "high",
    "generated_at": "2026-05-27T08:15:42Z"
  },
  "..."
}
```

**AI Risk Keywords:**
- `high` risk: refused, hostile, emergency, dangerous, damaged, unsafe, hazard, escalate, theft, assault
- `medium` risk: delayed, issue, complaint, incomplete, follow up, incorrect, failed
- `low` risk: everything else (normal visit)

---

## 3.6 Complete Visit

**`POST /visits/{id}/complete/`** — Field Agent (own) or Admin

Visit must currently be in `in_progress` status. Outcome is required.

**Request Body:**
```json
{
  "outcome": "successful"
}
```

| Outcome Value | When to use |
|---|---|
| `successful` | Job done, goal achieved |
| `failed` | Could not complete (access denied, hostile customer, etc.) |
| `partial` | Some work done, follow-up needed |

> `"pending"` is **not** a valid outcome when completing — the backend rejects it.

**Success Response (200):** Full `VisitDetail` object with:
- `status` changed to `"completed"`
- `completed_at` set to current server timestamp

**Error Responses:**
```json
// 400 — "pending" outcome not allowed on completion
{
  "error": true,
  "code": "BAD_REQUEST",
  "message": "Validation failed.",
  "details": {
    "outcome": ["Cannot complete a visit with outcome \"pending\". Choose: successful, failed, or partial."]
  }
}

// 400 — Visit not yet started
{
  "error": true,
  "code": "INVALID_STATE",
  "message": "Visit is currently \"scheduled\". Only in-progress visits can be completed.",
  "details": {}
}
```

---

## 3.7 Get AI Output

**`GET /visits/{id}/ai-output/`** — All roles

Fetches the stored AI analysis for a specific visit. Useful for supervisors checking risk flags on individual visits.

**Success Response (200):**
```json
{
  "summary": "Agent reported a successful inspection at the substation. Transformer was found in good condition with no immediate issues.",
  "follow_up": "No immediate follow-up required. Schedule next routine inspection in 3 months.",
  "risk_flag": "low",
  "generated_at": "2026-05-27T08:15:42Z"
}
```

**Error Responses:**
```json
// 404 — Notes not submitted yet, no AI output exists
{
  "error": true,
  "code": "NOT_FOUND",
  "message": "No AI output found. Submit visit notes first.",
  "details": {}
}
```

---

---

# MODULE 4 — Reports

> **Access:** Field Agent gets `403` on all report endpoints except Dashboard. Auditor has full read access.

---

## 4.1 Dashboard Summary

**`GET /reports/dashboard-summary/`** — All roles

Returns high-level counts, automatically scoped to the user's role.

**Success Response (200):**
```json
{
  "tasks": {
    "total": 10,
    "pending": 5,
    "in_progress": 2,
    "completed": 2,
    "cancelled": 1,
    "overdue": 1
  },
  "visits": {
    "total": 6,
    "scheduled": 1,
    "in_progress": 2,
    "completed_this_week": 3,
    "high_risk": 1
  },
  "role": "Team Lead",
  "scope": {
    "region": "North Zone",
    "team": "Alpha Team (North Zone)"
  }
}
```

**How to use it:** Use these numbers for the stat cards at the top of the dashboard. The `scope` field tells you what data the numbers represent (the user's region/team/all).

---

## 4.2 Pending Tasks Report

**`GET /reports/pending-tasks/`** — Admin, RM, TL, Auditor

Shows pending task counts grouped by Region and Team.

**Success Response (200):**
```json
{
  "count": 3,
  "results": [
    {
      "region": "North Zone",
      "region_id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
      "team": "Alpha Team",
      "team_id": "c1d2e3f4-a5b6-7890-cdef-1234567890ab",
      "pending_count": 2,
      "high_priority_count": 1
    },
    {
      "region": "North Zone",
      "region_id": "8bfa9412-f8ef-46dd-8432-fcba9d0b414d",
      "team": "Beta Team",
      "team_id": "d2e3f4a5-b6c7-8901-defa-234567890abc",
      "pending_count": 1,
      "high_priority_count": 0
    },
    {
      "region": "South Zone",
      "region_id": "9cfb0523-g9fg-57ee-9543-gdcb0e1c525e",
      "team": "Gamma Team",
      "team_id": "e3f4a5b6-c7d8-9012-efab-345678901bcd",
      "pending_count": 1,
      "high_priority_count": 1
    }
  ]
}
```

**How to use it:** Render as a grouped bar chart or sortable table. `high_priority_count` can be highlighted in red.

---

## 4.3 Agent Performance Report

**`GET /reports/agent-performance/`** — Admin, RM, TL, Auditor

Shows average task completion time per Field Agent.

**Success Response (200):**
```json
{
  "count": 2,
  "results": [
    {
      "agent_id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5",
      "agent_email": "agent2@fieldflow.com",
      "agent_name": "Field Agent Two",
      "total_completed": 1,
      "avg_hours_to_complete": 2.5
    },
    {
      "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "agent_email": "agent5@fieldflow.com",
      "agent_name": "Field Agent Five",
      "total_completed": 1,
      "avg_hours_to_complete": 1.8
    }
  ]
}
```

**How to use it:** Render as a leaderboard or bar chart sorted by `avg_hours_to_complete`. Lower = better performance.

---

## 4.4 Recent Visits Report

**`GET /reports/recent-visits/?days=30`** — Admin, RM, TL, Auditor

**Query Params:**
| Param | Default | Range | Purpose |
|---|---|---|---|
| `days` | 7 | 1–365 | How many days back to look |

**Success Response (200):**
```json
{
  "period_days": 30,
  "count": 3,
  "results": [
    {
      "agent": "agent1",
      "agent_email": "agent1@fieldflow.com",
      "visits_completed": 2,
      "successful": 1,
      "failed": 1,
      "partial": 0
    },
    {
      "agent": "agent2",
      "agent_email": "agent2@fieldflow.com",
      "visits_completed": 1,
      "successful": 0,
      "failed": 1,
      "partial": 0
    }
  ]
}
```

**How to use it:** Useful for a "Visit Outcomes" stacked bar chart. Each agent is one bar, split into successful/failed/partial segments.

---

## 4.5 Task Distribution Report

**`GET /reports/task-distribution/`** — Admin, RM, TL, Auditor

Shows how tasks created by each manager are distributed across statuses.

**Success Response (200):**
```json
{
  "count": 4,
  "results": [
    {
      "manager": "admin",
      "manager_email": "admin@fieldflow.com",
      "statuses": {
        "pending": 1,
        "completed": 1,
        "cancelled": 1
      },
      "total": 3
    },
    {
      "manager": "tl_alpha",
      "manager_email": "tl.alpha@fieldflow.com",
      "statuses": {
        "pending": 3,
        "in_progress": 1
      },
      "total": 4
    }
  ]
}
```

**How to use it:** Render as a stacked horizontal bar chart per manager. Good for workload distribution visualization.

---

---

# MODULE 5 — Activity Logs

> **Access:** Admin and Auditor see all logs. RM sees logs from actors in their region. TL sees logs from actors in their team. Field Agent: `403`.

---

## 5.1 List Activity Logs

**`GET /logs/`** — Admin, RM, TL, Auditor

**Query Params:**
| Param | Example | Purpose |
|---|---|---|
| `action` | `?action=task_assigned` | Filter by event type |
| `actor_id` | `?actor_id=<uuid>` | Filter by user who did the action |
| `target_type` | `?target_type=visit` | Filter by entity type: task, visit, user |
| `from` | `?from=2026-05-01` | Logs from this date onwards |
| `to` | `?to=2026-05-31` | Logs up to this date |
| `page` | `?page=1` | Pagination |

**All possible `action` values:**

| Action | When it's logged |
|---|---|
| `user_logged_in` | User logs in |
| `user_logged_out` | User logs out |
| `task_created` | A task is created |
| `task_assigned` | A task is assigned to an agent |
| `task_status_updated` | Task status changed |
| `visit_created` | A visit is created |
| `visit_started` | Visit moved to in_progress |
| `visit_completed` | Visit marked as completed |
| `visit_notes_added` | Notes added to a visit |
| `ai_output_generated` | AI processed visit notes |
| `user_created` | A new user account is created |
| `user_deactivated` | A user is deactivated |

**Success Response (200):**
```json
{
  "count": 12,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "actor": {
        "id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5",
        "username": "agent1",
        "email": "agent1@fieldflow.com",
        "full_name": "Field Agent One",
        "role_name": "Field Agent"
      },
      "action": "visit_notes_added",
      "target_type": "visit",
      "target_id": "657ee852-fb6b-4269-a462-2cf76856f083",
      "metadata": {
        "notes_length": 145,
        "ai_risk_flag": "high"
      },
      "timestamp": "2026-05-27T08:15:41Z"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "actor": {
        "id": "49407ea5-894a-4cc8-a639-8355513daf96",
        "username": "admin",
        "email": "admin@fieldflow.com",
        "full_name": "Admin User",
        "role_name": "Admin"
      },
      "action": "task_assigned",
      "target_type": "task",
      "target_id": "2a48155a-f635-41e0-bee6-fd9508b04493",
      "metadata": {
        "assigned_to": "agent1@fieldflow.com",
        "assigned_to_id": "f8a686f3-42ac-4f02-8530-b23c9574b4c5"
      },
      "timestamp": "2026-05-27T07:45:00Z"
    }
  ]
}
```

**How to use it:** Render as a scrollable timeline. The `action` field can be formatted into human-readable sentences (e.g., "agent1 added notes to visit at Sector 12"). Use `target_type` + `target_id` to create a deep link to the affected record.

---

## 5.2 Get Single Log Entry

**`GET /logs/{id}/`** — Admin, RM, TL, Auditor

Returns a single `ActivityLog` object (same shape as one item in `results` above).

---

---

# Quick Reference — All Endpoints

| # | Method | Endpoint | Access |
|---|---|---|---|
| 1 | POST | `/auth/login/` | Public |
| 2 | POST | `/auth/logout/` | All |
| 3 | POST | `/auth/token/refresh/` | Public |
| 4 | GET | `/auth/me/` | All |
| 5 | GET | `/users/` | Admin |
| 6 | POST | `/users/` | Admin |
| 7 | GET | `/users/{id}/` | Admin |
| 8 | PATCH | `/users/{id}/` | Admin |
| 9 | DELETE | `/users/{id}/` | Admin |
| 10 | GET | `/tasks/` | All (scoped) |
| 11 | POST | `/tasks/` | Admin, RM, TL |
| 12 | GET | `/tasks/{id}/` | All (scoped) |
| 13 | PATCH | `/tasks/{id}/` | Admin, RM, TL |
| 14 | DELETE | `/tasks/{id}/` | Admin |
| 15 | POST | `/tasks/{id}/assign/` | Admin, RM, TL |
| 16 | PATCH | `/tasks/{id}/status/` | All |
| 17 | GET | `/visits/` | All (scoped) |
| 18 | POST | `/visits/` | All |
| 19 | GET | `/visits/{id}/` | All (scoped) |
| 20 | POST | `/visits/{id}/start/` | Agent (own), Admin |
| 21 | POST | `/visits/{id}/complete/` | Agent (own), Admin |
| 22 | PATCH | `/visits/{id}/notes/` | Agent (own), Admin |
| 23 | GET | `/visits/{id}/ai-output/` | All (scoped) |
| 24 | GET | `/reports/dashboard-summary/` | All |
| 25 | GET | `/reports/pending-tasks/` | Admin, RM, TL, Auditor |
| 26 | GET | `/reports/agent-performance/` | Admin, RM, TL, Auditor |
| 27 | GET | `/reports/recent-visits/` | Admin, RM, TL, Auditor |
| 28 | GET | `/reports/task-distribution/` | Admin, RM, TL, Auditor |
| 29 | GET | `/logs/` | Admin, RM, TL, Auditor |
| 30 | GET | `/logs/{id}/` | Admin, RM, TL, Auditor |
