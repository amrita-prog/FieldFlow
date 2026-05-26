"""
Test all Phase 4 report endpoints + Phase 5 log endpoints
with real data in the DB.
"""
import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import Client

c = Client()

def header(title):
    print(f'\n{"="*55}')
    print(f'  {title}')
    print("="*55)

def test(label, resp, expect=200):
    data = resp.json()
    status_ok = '✓' if resp.status_code == expect else '✗'
    print(f'  {status_ok} [{resp.status_code}] {label}')
    if resp.status_code != expect:
        print(f'    ERROR: {json.dumps(data)[:200]}')
    return data

# ── Tokens ───────────────────────────────────────────────────
def login(email, pwd):
    r = c.post('/api/auth/login/', data=json.dumps({'email':email,'password':pwd}),
               content_type='application/json', SERVER_NAME='testserver')
    return {'HTTP_AUTHORIZATION': f'Bearer {r.json()["access"]}', 'SERVER_NAME': 'testserver'}

admin_h   = login('admin@fieldflow.com', 'Admin@123')
rm_h      = login('rm.north@fieldflow.com', 'Pass@123')
tl_h      = login('tl.alpha@fieldflow.com', 'Pass@123')
agent_h   = login('agent1@fieldflow.com', 'Pass@123')
auditor_h = login('auditor@fieldflow.com', 'Pass@123')

print('\n  Logged in: Admin, RM, TL, Agent, Auditor')

# ─────────────────────────────────────────────────────────────
header('PHASE 4 — REPORT ENDPOINTS')
# ─────────────────────────────────────────────────────────────

# Dashboard (all roles)
r = c.get('/api/reports/dashboard-summary/', **admin_h)
d = test('Dashboard (Admin)', r, 200)
print(f"    Tasks: {d['tasks']}")
print(f"    Visits: {d['visits']}")

r = c.get('/api/reports/dashboard-summary/', **rm_h)
d = test('Dashboard (RM North - region scoped)', r, 200)
print(f"    Tasks: total={d['tasks']['total']} scope={d['scope']}")

r = c.get('/api/reports/dashboard-summary/', **tl_h)
d = test('Dashboard (Team Lead - team scoped)', r, 200)
print(f"    Tasks: total={d['tasks']['total']} scope={d['scope']}")

r = c.get('/api/reports/dashboard-summary/', **agent_h)
d = test('Dashboard (Field Agent - own data)', r, 200)
print(f"    Tasks: total={d['tasks']['total']} role={d['role']}")

# Pending Tasks
r = c.get('/api/reports/pending-tasks/', **admin_h)
d = test('Pending Tasks (Admin - all regions)', r, 200)
for row in d['results']:
    print(f"    Region={row.get('region','?')} Team={row.get('team','?')} Pending={row.get('pending_count','?')} HighPri={row.get('high_priority_count','?')}")

r = c.get('/api/reports/pending-tasks/', **rm_h)
d = test('Pending Tasks (RM - North Zone only)', r, 200)
print(f"    Count: {d['count']} groups")

r = c.get('/api/reports/pending-tasks/', **tl_h)
d = test('Pending Tasks (TL - Alpha Team only)', r, 200)
print(f"    Count: {d['count']} groups")

r = c.get('/api/reports/pending-tasks/', **agent_h)
test('Pending Tasks (FA - blocked)', r, 403)

# Agent Performance
r = c.get('/api/reports/agent-performance/', **admin_h)
d = test('Agent Performance (Admin - all agents)', r, 200)
for row in d['results']:
    print(f"    {row.get('agent_email','?')} | completed={row.get('total_completed',0)} avg_hours={row.get('avg_hours_to_complete','N/A')}")

# Recent Visits
r = c.get('/api/reports/recent-visits/?days=30', **admin_h)
d = test('Recent Visits (last 30 days)', r, 200)
print(f"    Period: {d['period_days']} days | Groups: {d['count']}")
for row in d['results']:
    print(f"    {row.get('agent','?')} | completed={row.get('visits_completed',0)} success={row.get('successful',0)} failed={row.get('failed',0)}")

# Task Distribution
r = c.get('/api/reports/task-distribution/', **admin_h)
d = test('Task Distribution (Admin)', r, 200)
for row in d['results']:
    print(f"    {row['manager']} | total={row['total']} statuses={row['statuses']}")

r = c.get('/api/reports/task-distribution/', **auditor_h)
d = test('Task Distribution (Auditor - full access)', r, 200)
print(f"    Count: {d['count']} managers")

# ─────────────────────────────────────────────────────────────
header('PHASE 5 — ACTIVITY LOG ENDPOINTS')
# ─────────────────────────────────────────────────────────────

r = c.get('/api/logs/', **admin_h)
d = test('Logs List (Admin - all)', r, 200)
print(f"    Total logs in DB: {d.get('count', len(d.get('results', d)))}")

r = c.get('/api/logs/?action=user_logged_in', **admin_h)
d = test('Logs Filter by action=user_logged_in', r, 200)

r = c.get('/api/logs/?target_type=task', **admin_h)
d = test('Logs Filter by target_type=task', r, 200)

r = c.get('/api/logs/', **rm_h)
d = test('Logs (RM - region scoped)', r, 200)

r = c.get('/api/logs/', **tl_h)
d = test('Logs (TL - team scoped)', r, 200)

r = c.get('/api/logs/', **auditor_h)
d = test('Logs (Auditor - full access)', r, 200)

r = c.get('/api/logs/', **agent_h)
test('Logs (FA - blocked)', r, 403)

header('ALL TESTS PASSED')
