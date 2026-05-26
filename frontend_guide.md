# Field Force Management System — Frontend Guide

## Project Overview

A role-based field operations web app where five types of users (Admin, Regional Manager, Team Lead, Field Agent, Auditor) interact with tasks, visits, and reports. Each user sees only the data and actions their role allows. The frontend is a React SPA that talks to the Django REST backend via JWT-authenticated API calls.

---

## Tech Stack

- **Framework**: React (Vite)
- **Routing**: React Router v6
- **State/Auth**: React Context API (AuthContext)
- **HTTP Client**: Axios with JWT interceptor (auto-refresh on 401)
- **UI**: Vanilla CSS or any component library (Ant Design / shadcn recommended)
- **HTTP Testing**: `test.http` (REST Client for VS Code)

---

## Folder Structure

```
frontend/
├── public/
├── src/
│   ├── api/               ← axios instance + all API call functions
│   │   ├── axios.js       ← base instance with interceptors
│   │   ├── auth.js
│   │   ├── tasks.js
│   │   ├── visits.js
│   │   ├── reports.js
│   │   └── logs.js
│   ├── context/
│   │   └── AuthContext.jsx  ← user, role, permissions, login(), logout()
│   ├── components/
│   │   ├── Sidebar.jsx      ← role-aware nav
│   │   ├── ProtectedRoute.jsx
│   │   ├── RoleBadge.jsx
│   │   ├── StatusBadge.jsx
│   │   ├── RiskBadge.jsx
│   │   └── Pagination.jsx
│   ├── pages/
│   │   ├── Login/
│   │   ├── Dashboard/
│   │   ├── Tasks/
│   │   ├── Visits/
│   │   ├── Reports/
│   │   ├── Logs/
│   │   └── Users/
│   ├── hooks/
│   │   ├── useAuth.js
│   │   └── usePermission.js  ← checks if user can do action on module
│   └── App.jsx
```

---

## Auth Flow

1. User visits `/login` → submits email + password
2. Frontend calls `POST /api/auth/login/`
3. Response: `{ access, refresh, user: { id, username, role, permissions[] } }`
4. Store `access` in memory (or sessionStorage), `refresh` in localStorage
5. Store `user` object in `AuthContext`
6. Redirect to `/dashboard`
7. Axios interceptor attaches `Authorization: Bearer <access>` to every request
8. On 401 → interceptor calls `POST /api/auth/token/refresh/` → retries original request
9. On logout → call `POST /api/auth/logout/` → clear all tokens → redirect to `/login`

---

## Role-Aware Sidebar

```
Admin          → Dashboard, Tasks, Visits, Reports, Logs, Users
Regional Mgr   → Dashboard, Tasks, Visits, Reports, Logs
Team Lead      → Dashboard, Tasks, Visits, Reports, Logs
Field Agent    → Dashboard, My Tasks, My Visits
Auditor        → Dashboard, Reports, Logs
```

---

## Pages

---

### 1. Login Page
**Route**: `/login`  
**Access**: Public (redirect to dashboard if already logged in)

**Layout**:
- Centered card with app name and logo
- Email input
- Password input with show/hide toggle
- Login button with loading state
- Error message on wrong credentials

**Behavior**:
- On success → save tokens, set AuthContext, push to `/dashboard`
- On 401 → show "Invalid email or password"
- On network error → show "Server unreachable"

---

### 2. Dashboard
**Route**: `/dashboard`  
**Access**: All roles (data scoped per role on the backend)

**Layout**:
- Row of summary cards:
  - Total Tasks
  - Pending Tasks
  - In-Progress Tasks
  - Tasks Completed Today
  - Visits This Week
  - High-Risk Visits (risk_flag = high)
- Recent activity table (last 10 log entries) — hidden for Field Agent
- Quick links: "Create Task" (if has permission), "My Visits" (Field Agent)

**API calls**:
- `GET /api/reports/dashboard-summary/`
- `GET /api/logs/?page_size=10` (if role allows)

---

### 3. Task List Page
**Route**: `/tasks`  
**Access**: All roles (scoped)

**Layout**:
- Page header with title + "Create Task" button (hidden for Field Agent and Auditor)
- Filter bar: Status dropdown, Priority dropdown, Due Date picker, Search input
- Table columns: Title, Status, Priority, Assigned To, Region, Team, Due Date, Actions
- Each row → click → navigate to `/tasks/:id`
- Pagination controls at bottom

**Behavior**:
- On load → `GET /api/tasks/` with any active filter params
- Filter changes → re-fetch with new params
- Admin/RM/TL see all visible tasks; Field Agent sees only their own
- Status shown as colored badge

**API calls**:
- `GET /api/tasks/?status=&priority=&search=&page=`

---

### 4. Task Detail Page
**Route**: `/tasks/:id`  
**Access**: All roles (within scope)

**Layout**:
- Back button → `/tasks`
- Task header: title, priority badge, status badge
- Info grid: Created By, Assigned To, Region, Team, Due Date, Created At
- Description section (full text)
- "Assign Task" section (Admin/RM/TL only): agent dropdown + Assign button
- "Update Status" section (Admin/RM/TL/Field Agent): status dropdown + Update button
- Linked Visits section: table of visits for this task with status + outcome

**API calls**:
- `GET /api/tasks/:id/`
- `POST /api/tasks/:id/assign/`
- `PATCH /api/tasks/:id/status/`
- `GET /api/visits/?task=:id`

---

### 5. Create Task Page
**Route**: `/tasks/new`  
**Access**: Admin, Regional Manager, Team Lead

**Layout**:
- Form fields:
  - Title (required)
  - Description (textarea)
  - Priority (dropdown: low / medium / high / critical)
  - Due Date (date picker)
  - Region (dropdown — from API, pre-selected from user's region if RM/TL)
  - Team (dropdown — filtered by region)
  - Assigned To (optional agent dropdown — filtered by team)
- Submit button + Cancel link

**API calls**:
- `POST /api/tasks/`
- `GET /api/users/?role=Field Agent` (for agent dropdown)

---

### 6. Visit List Page
**Route**: `/visits`  
**Access**: All roles (scoped)

**Layout**:
- Filter bar: Status dropdown, Outcome dropdown, Date range
- Table columns: Location, Agent, Task (linked), Status, Outcome, Started At, Completed At
- Each row → click → `/visits/:id`
- Pagination

**API calls**:
- `GET /api/visits/?status=&outcome=&page=`

---

### 7. Visit Detail Page
**Route**: `/visits/:id`  
**Access**: All roles (within scope)

**Layout**:
- Visit info header: location, status badge, outcome badge
- Info grid: Agent, Task, Started At, Completed At, Created At
- Notes section: shows current notes text
- **AI Output card** (shown if AI output exists):
  - Summary paragraph
  - Risk Flag badge (color-coded: red=high, orange=medium, green=low)
  - Follow-up recommendation text
  - Generated At timestamp
- Action buttons (Field Agent only, own visit only):
  - "Start Visit" (if status = scheduled)
  - "Add Notes / Complete" (if status = in_progress) → opens form below

**API calls**:
- `GET /api/visits/:id/`
- `POST /api/visits/:id/start/`

---

### 8. Visit Notes / Complete Form
**Route**: Inline on `/visits/:id` (not a separate page)  
**Access**: Field Agent (own visit, status = in_progress)

**Layout** (expandable panel below Visit Detail):
- Notes textarea (required)
- Outcome dropdown: successful / failed / partial
- "Submit Notes" button
- After submit: AI Output card refreshes with new data
- "Complete Visit" button (separate, enabled only after notes submitted)

**API calls**:
- `PATCH /api/visits/:id/notes/`
- `POST /api/visits/:id/complete/`

---

### 9. Reports Page
**Route**: `/reports`  
**Access**: Admin, Regional Manager, Team Lead, Auditor

**Layout**:
- Tab bar: Pending Tasks | Agent Performance | Recent Visits | Task Distribution
- Each tab shows a table + optional summary text
- Dashboard Summary section always visible at top (reuses dashboard API)

**Tab: Pending Tasks**
- Table: Region, Team, Pending Count, High Priority Count, Earliest Due Date

**Tab: Agent Performance**
- Table: Agent Name, Email, Completed Tasks, Avg Hours to Complete

**Tab: Recent Visits (Last 7 Days)**
- Table: Agent, Team, Region, Visits Completed, Successful, Failed, Avg Minutes

**Tab: Task Distribution**
- Table: Manager, Status, Count, Percentage

**API calls**:
- `GET /api/reports/pending-tasks/`
- `GET /api/reports/agent-performance/`
- `GET /api/reports/recent-visits/`
- `GET /api/reports/task-distribution/`

---

### 10. Activity Logs Page
**Route**: `/logs`  
**Access**: Admin, Regional Manager, Team Lead, Auditor

**Layout**:
- Filter bar: Action dropdown, Actor search, Target Type dropdown, From date, To date
- Table columns: Timestamp, Actor, Action (badge), Target Type, Target ID, Metadata (collapsed JSON)
- Click row → expand to show full metadata JSON
- Pagination

**API calls**:
- `GET /api/logs/?action=&actor_id=&from=&to=&page=`

---

### 11. User Management Page
**Route**: `/users`  
**Access**: Admin only

**Layout**:
- "Create User" button → opens a modal or navigates to `/users/new`
- Table columns: Username, Email, Role badge, Region, Team, Active status, Actions
- Actions per row: Edit, Deactivate (no hard delete)
- Create/Edit form fields: username, email, password (create only), role, region, team

**API calls**:
- `GET /api/users/`
- `POST /api/users/`
- `PATCH /api/users/:id/`
- `DELETE /api/users/:id/` (soft delete → sets is_active=False)

---

## Role → Page Access Matrix

| Page | Admin | Regional Mgr | Team Lead | Field Agent | Auditor |
|---|---|---|---|---|---|
| Login | ✅ | ✅ | ✅ | ✅ | ✅ |
| Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| Task List | ✅ all | ✅ region | ✅ team | ✅ own | ✅ all |
| Task Detail | ✅ | ✅ | ✅ | ✅ own | ✅ |
| Create Task | ✅ | ✅ | ✅ | ❌ | ❌ |
| Visit List | ✅ all | ✅ region | ✅ team | ✅ own | ✅ all |
| Visit Detail | ✅ | ✅ | ✅ | ✅ own | ✅ |
| Visit Notes Form | ✅ | ❌ | ❌ | ✅ own | ❌ |
| Reports | ✅ | ✅ scoped | ✅ scoped | ❌ | ✅ all |
| Logs | ✅ all | ✅ region | ✅ team | ❌ | ✅ all |
| User Management | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## Shared Components

| Component | Purpose |
|---|---|
| `Sidebar` | Role-aware navigation links |
| `ProtectedRoute` | Redirects to `/login` if no token |
| `RoleBadge` | Colored pill for role name |
| `StatusBadge` | Color-coded task/visit status |
| `RiskBadge` | Red/Orange/Green for AI risk_flag |
| `Pagination` | Reusable page controls |

---

## `usePermission` Hook

```js
const { can } = usePermission()
// can('tasks', 'create') → true/false
// can('visits', 'update') → true/false
// Uses permissions[] array from AuthContext
```

Used to conditionally render buttons, forms, and menu items without extra API calls.
