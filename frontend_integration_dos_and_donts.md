# FieldFlow Frontend Integration — Do's & Don'ts 

This is a quick reference guide for connecting the React frontend to the Django REST backend.

## 🟢 DO (What you should do)

1. **DO use an Axios Interceptor for Auth**
   The backend uses short-lived `access` tokens and long-lived `refresh` tokens. Catch `401 Unauthorized` responses globally, call `/api/auth/token/refresh/` with your saved refresh token, and seamlessly retry the failed request.

2. **DO dynamically render the UI based on `/auth/me/`**
   After login, hit `/api/auth/me/`. It returns the user's `role` and an array of `module_permissions`. Use this to hide menus/buttons. If `can_create` is false for tasks, hide the "New Task" button. Don't hardcode logic like `if (role === 'Admin')`.

3. **DO handle the standard error shape**
   Every backend error (validation, permission, etc.) returns:
   `{ "error": true, "code": "...", "message": "...", "details": {} }`
   Show the `message` field in your UI Toast/Snackbar notifications. Use the `details` object to show field-specific form validation errors.

4. **DO use pagination parameters**
   Endpoints like `/api/tasks/` and `/api/visits/` are paginated. Append `?page=X` to your GET requests. Use the `count`, `next`, and `previous` fields from the response to build your pagination controls.

5. **DO use the custom action endpoints for state changes**
   Don't try to manually update a task's status or a visit's `started_at` time via a standard `PUT` request. Use the dedicated endpoints (`/visits/{id}/start/`, `/tasks/{id}/status/`). They handle backend validation, AI triggers, and audit logging automatically.

---

## 🔴 DON'T (What you should avoid)

1. **DO NOT worry about data scoping or filtering manually**
   You don't need to pass `?agent_id=123` to get a Field Agent's tasks. Just call `GET /api/tasks/`. The backend automatically knows who is logged in via the token and will strictly return *only* the data they are allowed to see.

2. **DO NOT send full objects on PATCH requests**
   If you are updating just a task's priority, only send `{ "priority": "high" }`. The backend uses `PATCH` to allow partial updates.

3. **DO NOT hardcode UUIDs in your frontend**
   Entities (Users, Tasks, Visits, Regions, Teams) use UUIDs (e.g., `550e8400-e29b-41d4-a716-446655440000`) instead of integers. Treat them as strings. Do not try to parse them or assume their format.

4. **DO NOT crash on 403 Forbidden**
   If a user navigates directly to a URL they shouldn't access (like a Field Agent hitting the Reports page), the backend will return a `403`. Catch this gracefully in the frontend and show an "Access Denied" or "Not Authorized" empty state component.

5. **DO NOT worry about backend architecture / DB structure**
   Focus entirely on the JSON payloads. The backend handles all complex relationships, timestamps, and AI integration behind the scenes.
