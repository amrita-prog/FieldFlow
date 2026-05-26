"""
Seed sample tasks and visits for Phase 4 report testing.
Run with: python manage.py shell < scripts/seed_sample_data.py
OR:       python scripts/seed_sample_data.py (from project root)
"""
import os
import django
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from datetime import date, timedelta
from django.utils import timezone

from accounts.models import User, Region, Team
from tasks.models import Task
from visits.models import Visit, AIOutput
from ai_service.service import MockAIService
from logs.utils import log_activity

# ── Get seeded objects ────────────────────────────────────────
admin      = User.objects.get(email='admin@fieldflow.com')
rm_north   = User.objects.get(email='rm.north@fieldflow.com')
tl_alpha   = User.objects.get(email='tl.alpha@fieldflow.com')
tl_beta    = User.objects.get(email='tl.beta@fieldflow.com')
tl_gamma   = User.objects.get(email='tl.gamma@fieldflow.com')
agent1     = User.objects.get(email='agent1@fieldflow.com')
agent2     = User.objects.get(email='agent2@fieldflow.com')
agent3     = User.objects.get(email='agent3@fieldflow.com')
agent4     = User.objects.get(email='agent4@fieldflow.com')
agent5     = User.objects.get(email='agent5@fieldflow.com')
north_zone = Region.objects.get(name='North Zone')
south_zone = Region.objects.get(name='South Zone')
alpha_team = Team.objects.get(name='Alpha Team')
beta_team  = Team.objects.get(name='Beta Team')
gamma_team = Team.objects.get(name='Gamma Team')

today = date.today()
now   = timezone.now()

print('[seed_sample_data] Creating sample tasks...')

# ── Tasks ─────────────────────────────────────────────────────
tasks_data = [
    ('Inspect Main Transformer T-12',         tl_alpha, agent1, north_zone, alpha_team, 'high',     'pending',     today + timedelta(days=5)),
    ('Customer Survey - Block A',              tl_alpha, agent1, north_zone, alpha_team, 'medium',   'in_progress', today + timedelta(days=10)),
    ('Replace Fuse Units - Building 7',        admin,    agent2, north_zone, alpha_team, 'critical', 'completed',   today - timedelta(days=2)),
    ('Monthly Safety Check - North',           tl_alpha, agent3, north_zone, beta_team,  'low',      'pending',     today - timedelta(days=1)),  # overdue
    ('Line Fault Investigation - Sector 3',    tl_beta,  agent3, north_zone, beta_team,  'high',     'pending',     today + timedelta(days=3)),
    ('Meter Reading - Zone B',                 tl_gamma, agent4, south_zone, gamma_team, 'medium',   'in_progress', today + timedelta(days=7)),
    ('Disconnect Notice Delivery - Block 5',   tl_gamma, agent5, south_zone, gamma_team, 'medium',   'completed',   today - timedelta(days=5)),
    ('Emergency Repair - Substation 4',        admin,    agent4, south_zone, gamma_team, 'critical', 'pending',     today + timedelta(days=1)),
    ('Annual Equipment Audit',                 admin,    agent5, south_zone, gamma_team, 'low',      'cancelled',   today + timedelta(days=30)),
    ('Customer Complaint Follow-up - Apt 12',  tl_alpha, agent1, north_zone, alpha_team, 'medium',   'pending',     today + timedelta(days=2)),
]

created_tasks = []
for title, created_by, assigned_to, region, team, priority, status, due_date in tasks_data:
    t, created = Task.objects.get_or_create(
        title=title,
        defaults={
            'created_by': created_by,
            'assigned_to': assigned_to,
            'region': region,
            'team': team,
            'priority': priority,
            'status': status,
            'due_date': due_date,
        }
    )
    created_tasks.append(t)
    print(f'  {"[NEW]" if created else "[EXISTS]"} Task: {title[:50]} [{status}]')

print(f'\n[seed_sample_data] Creating sample visits...')

# ── Visits ────────────────────────────────────────────────────
t0, t1, t2, t3, t4, t5, t6, t7, t8, t9 = created_tasks

visits_data = [
    # (task, agent, location, status, outcome, notes, hours_ago_start, hours_ago_end)
    (t0, agent1, 'Sector 12 Main Substation',        'completed', 'successful',
     'Inspection completed. Transformer found in good working condition. No immediate action required.',
     now - timedelta(hours=5), now - timedelta(hours=2)),

    (t2, agent2, 'Building 7, North Zone Industrial', 'completed', 'failed',
     'Customer refused entry and was hostile. Urgent escalation required. Facility appears damaged and there is a safety hazard on the premises.',
     now - timedelta(days=1, hours=4), now - timedelta(days=1, hours=1)),

    (t6, agent5, 'Block 5, South Residential',       'completed', 'successful',
     'Disconnect notice delivered successfully. Customer acknowledged receipt.',
     now - timedelta(days=5, hours=3), now - timedelta(days=5, hours=1)),

    (t1, agent1, 'Block A Community Center',          'in_progress', 'pending',
     'Visit delayed due to traffic. Partial work completed so far. Need follow up.',
     now - timedelta(hours=2), None),

    (t5, agent4, 'Zone B Meter Station',              'in_progress', 'pending',
     'Started meter reading. Issue found with unit 4B - incomplete currently.',
     now - timedelta(hours=1), None),

    (t9, agent1, 'Apartment Complex 12, North Zone',  'scheduled', 'pending',
     '', None, None),
]

service = MockAIService()
for task, agent, location, vstatus, outcome, notes, started, completed in visits_data:
    v, created = Visit.objects.get_or_create(
        task=task,
        agent=agent,
        defaults={
            'location': location,
            'status': vstatus,
            'outcome': outcome,
            'notes': notes,
            'started_at': started,
            'completed_at': completed,
        }
    )

    # Generate AI output if notes provided
    if notes and notes.strip() and created:
        ai_data = service.generate_output(notes=notes, visit=v)
        AIOutput.objects.update_or_create(
            visit=v,
            defaults={
                'summary': ai_data['summary'],
                'follow_up': ai_data['follow_up'],
                'risk_flag': ai_data['risk_flag'],
            }
        )
        print(f'  {"[NEW]" if created else "[EXISTS]"} Visit: {location[:45]} | AI risk: {ai_data["risk_flag"]}')
    else:
        print(f'  {"[NEW]" if created else "[EXISTS]"} Visit: {location[:45]} | No AI (no notes)')

# ── Summary ───────────────────────────────────────────────────
print(f'\n[seed_sample_data] Final counts:')
print(f'  Tasks:     {Task.objects.count()}')
print(f'  Visits:    {Visit.objects.count()}')
print(f'  AIOutputs: {AIOutput.objects.count()}')
print('\n[DONE] Sample data ready for report testing.')
