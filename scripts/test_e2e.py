"""
scripts/test_e2e.py

Full end-to-end test for all 5 phases.
Covers the complete realistic user journey:
  1. Admin logs in, creates a task, assigns to agent
  2. Agent logs in, starts a visit, adds notes (AI generated)
  3. Agent completes visit
  4. TL checks reports and logs
  5. All access control rules verified

Run via:
  python manage.py shell --no-imports -c "exec(open('scripts/test_e2e.py').read())"
"""
import json
from django.test import Client

c = Client()
PASS_SYMBOL = '[PASS]'
FAIL_SYMBOL = '[FAIL]'

results = {'passed': 0, 'failed': 0}

def check(label, resp, expected_status, check_key=None, check_val=None):
    data = resp.json() if resp.headers.get('content-type','').startswith('application/json') else {}
    ok = resp.status_code == expected_status
    if ok and check_key and isinstance(data, dict):
        ok = data.get(check_key) == check_val
    symbol = PASS_SYMBOL if ok else FAIL_SYMBOL
    results['passed' if ok else 'failed'] += 1
    print(f'  {symbol} [{resp.status_code}] {label}')
    if not ok:
        print(f'         Expected: {expected_status} | Got: {resp.status_code}')
        if check_key:
            print(f'         Expected {check_key}={check_val} | Got: {data.get(check_key)}')
        print(f'         Body: {str(data)[:200]}')
    return data

def login(email, pwd):
    r = c.post('/api/auth/login/', data=json.dumps({'email':email,'password':pwd}),
               content_type='application/json', SERVER_NAME='testserver')
    token = r.json()['access']
    return {'HTTP_AUTHORIZATION': f'Bearer {token}', 'SERVER_NAME': 'testserver'}, r.json()['user']['id']

def post(url, data, headers):
    return c.post(url, data=json.dumps(data), content_type='application/json', **headers)

def patch(url, data, headers):
    return c.patch(url, data=json.dumps(data), content_type='application/json', **headers)

def get(url, headers):
    return c.get(url, **headers)

def delete(url, headers):
    return c.delete(url, **headers)

# ──────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('  FIELDFLOW — FULL END-TO-END TEST SUITE')
print('='*60)

# ──────────────────────────────────────────────────────────────
print('\n--- PHASE 1: Auth & Users ---')
# ──────────────────────────────────────────────────────────────

admin_h, admin_id     = login('admin@fieldflow.com',   'Admin@123')
rm_h,    rm_id        = login('rm.north@fieldflow.com', 'Pass@123')
tl_h,    tl_id        = login('tl.alpha@fieldflow.com', 'Pass@123')
agent_h, agent1_id    = login('agent1@fieldflow.com',   'Pass@123')
agt2_h,  agent2_id    = login('agent2@fieldflow.com',   'Pass@123')
audit_h, _            = login('auditor@fieldflow.com',  'Pass@123')

# Me endpoint
r = get('/api/auth/me/', admin_h)
check('GET /auth/me/ returns user data', r, 200, 'email', 'admin@fieldflow.com')

# Wrong credentials
r = post('/api/auth/login/', {'email':'admin@fieldflow.com','password':'wrong'}, {'SERVER_NAME':'testserver'})
check('Wrong password -> 400 (validation error)', r, 400)

# No auth
r = c.get('/api/auth/me/', SERVER_NAME='testserver')
check('No token -> 401', r, 401)

# User list (Admin)
r = get('/api/users/', admin_h)
check('Admin can list users', r, 200)

# User list (Agent -> 403)
r = get('/api/users/', agent_h)
check('Field Agent cannot list users -> 403', r, 403)

# ──────────────────────────────────────────────────────────────
print('\n--- PHASE 2: Tasks ---')
# ──────────────────────────────────────────────────────────────

# Create task as TL
r = post('/api/tasks/', {
    'title': 'E2E Test Task',
    'description': 'Created by Team Lead in e2e test',
    'priority': 'high',
    'due_date': '2026-12-31',
}, tl_h)
task = check('TL creates task -> 201', r, 201)
task_id = task.get('id')

# Admin sees all tasks
r = get('/api/tasks/', admin_h)
check('Admin lists tasks (sees all)', r, 200)

# Agent sees only own tasks
r = get('/api/tasks/', agent_h)
check('Agent lists tasks (own only)', r, 200)

# Assign task to agent1
if task_id:
    r = post(f'/api/tasks/{task_id}/assign/', {'assigned_to_id': agent1_id}, tl_h)
    check(f'TL assigns task to agent1', r, 200)

    # Status: pending -> in_progress
    r = patch(f'/api/tasks/{task_id}/status/', {'status': 'in_progress'}, agent_h)
    check('Agent moves task pending -> in_progress', r, 200)

    # Invalid: in_progress -> pending (backward)
    r = patch(f'/api/tasks/{task_id}/status/', {'status': 'pending'}, agent_h)
    check('Invalid status transition -> 400', r, 400)

    # Status: in_progress -> completed
    r = patch(f'/api/tasks/{task_id}/status/', {'status': 'completed'}, agent_h)
    check('Agent completes task', r, 200)

    # Assign non-agent (TL) -> 400
    r = post(f'/api/tasks/{task_id}/assign/', {'assigned_to_id': tl_id}, tl_h)
    check('Assign non-Field-Agent -> 400', r, 400)

    # Past due_date -> 400
    r = post('/api/tasks/', {'title':'Old','priority':'low','due_date':'2020-01-01'}, admin_h)
    check('Past due_date rejected -> 400', r, 400)

    # FA cannot delete task
    r = delete(f'/api/tasks/{task_id}/', agent_h)
    check('FA cannot delete task -> 403', r, 403)

# ──────────────────────────────────────────────────────────────
print('\n--- PHASE 3: Visits & AI ---')
# ──────────────────────────────────────────────────────────────

# Create visit as agent1 (self-assigned)
r = post('/api/visits/', {'location': 'E2E Test Site, Sector 99'}, agent_h)
visit = check('Agent1 creates visit -> 201', r, 201)
visit_id = visit.get('id')

if visit_id:
    # Start visit
    r = post(f'/api/visits/{visit_id}/start/', {}, agent_h)
    check('Agent starts visit -> 200', r, 200)

    # Double-start -> 400
    r = post(f'/api/visits/{visit_id}/start/', {}, agent_h)
    check('Double-start visit -> 400', r, 400)

    # Agent2 cannot start agent1's visit
    r = post(f'/api/visits/{visit_id}/start/', {}, agt2_h)
    check('Agent2 cannot start agent1 visit -> 403', r, 403)

    # Add notes (HIGH risk) -> AI generated
    r = patch(f'/api/visits/{visit_id}/notes/', {
        'notes': 'Customer refused entry and was hostile. Urgent escalation required. Facility appears damaged.',
        'outcome': 'failed'
    }, agent_h)
    d = check('Agent adds HIGH RISK notes -> 200 + AI output', r, 200)
    ai = d.get('ai_output', {})
    if ai.get('risk_flag') == 'high':
        print(f'         AI risk_flag = high [PASS]')
        results['passed'] += 1
    else:
        print(f'         AI risk_flag should be high, got: {ai.get("risk_flag")} [FAIL]')
        results['failed'] += 1

    # Get AI output endpoint
    r = get(f'/api/visits/{visit_id}/ai-output/', admin_h)
    check('GET /visits/{id}/ai-output/ -> 200', r, 200)

    # Complete visit
    r = post(f'/api/visits/{visit_id}/complete/', {'outcome': 'failed'}, agent_h)
    check('Agent completes visit with outcome -> 200', r, 200)

    # Complete with "pending" outcome -> 400
    r2 = post('/api/visits/', {'location': 'Another Site'}, agent_h)
    v2 = r2.json()
    v2_id = v2.get('id')
    if v2_id:
        post(f'/api/visits/{v2_id}/start/', {}, agent_h)
        r = post(f'/api/visits/{v2_id}/complete/', {'outcome': 'pending'}, agent_h)
        check('Complete with pending outcome -> 400', r, 400)

    # Notes on cancelled visit -> 400 (visit was just completed, so actually completed state)
    r = patch(f'/api/visits/{visit_id}/notes/', {'notes': 'Notes on done visit are ok actually'}, agent_h)
    # completed visits can still get notes updated, only cancelled blocks
    check('Notes on completed visit -> 200 (only cancelled blocks)', r, 200)

# ──────────────────────────────────────────────────────────────
print('\n--- PHASE 4: Reports ---')
# ──────────────────────────────────────────────────────────────

r = get('/api/reports/dashboard-summary/', admin_h)
check('Admin dashboard -> 200', r, 200)

r = get('/api/reports/dashboard-summary/', agent_h)
check('Agent dashboard (own data) -> 200', r, 200)

r = get('/api/reports/pending-tasks/', admin_h)
check('Pending tasks (Admin) -> 200', r, 200)

r = get('/api/reports/pending-tasks/', rm_h)
check('Pending tasks (RM scoped) -> 200', r, 200)

r = get('/api/reports/pending-tasks/', agent_h)
check('Pending tasks (FA) -> 403', r, 403)

r = get('/api/reports/agent-performance/', admin_h)
check('Agent performance -> 200', r, 200)

r = get('/api/reports/recent-visits/?days=30', admin_h)
check('Recent visits (30 days) -> 200', r, 200)

r = get('/api/reports/task-distribution/', audit_h)
check('Task distribution (Auditor) -> 200', r, 200)

# ──────────────────────────────────────────────────────────────
print('\n--- PHASE 5: Activity Logs ---')
# ──────────────────────────────────────────────────────────────

r = get('/api/logs/', admin_h)
check('Admin logs -> 200', r, 200)

r = get('/api/logs/?action=user_logged_in', admin_h)
check('Filter logs by action -> 200', r, 200)

r = get('/api/logs/?target_type=task', admin_h)
check('Filter logs by target_type -> 200', r, 200)

r = get('/api/logs/', audit_h)
check('Auditor logs -> 200', r, 200)

r = get('/api/logs/', rm_h)
check('RM logs (region scoped) -> 200', r, 200)

r = get('/api/logs/', agent_h)
check('FA logs -> 403', r, 403)

# ──────────────────────────────────────────────────────────────
print('\n' + '='*60)
total = results['passed'] + results['failed']
print(f'  RESULTS: {results["passed"]}/{total} passed | {results["failed"]} failed')
print('='*60)
if results['failed'] == 0:
    print('  ALL TESTS PASSED')
else:
    print(f'  {results["failed"]} TEST(S) FAILED — review above')
print('='*60 + '\n')
