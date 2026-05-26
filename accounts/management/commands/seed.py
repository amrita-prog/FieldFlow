"""
accounts/management/commands/seed.py

Run with: python manage.py seed
Re-runnable safely — uses get_or_create throughout.

Creates:
  - 5 roles with module permissions
  - 2 regions, 3 teams
  - 1 Admin, 2 Regional Managers, 3 Team Leads, 5 Field Agents, 1 Auditor
  - EmployeeProfile for every user

Credentials printed to console after seeding.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Role, ModulePermission, Region, Team, User, EmployeeProfile


# ─────────────────────────────────────────────────────────────
# Permission matrix: role → module → (create, read, update, delete, scope)
# ─────────────────────────────────────────────────────────────
PERMISSION_MATRIX = {
    'Admin': {
        'tasks':   (True,  True,  True,  True,  'all'),
        'visits':  (True,  True,  True,  True,  'all'),
        'reports': (False, True,  False, False, 'all'),
        'logs':    (False, True,  False, False, 'all'),
        'users':   (True,  True,  True,  True,  'all'),
    },
    'Regional Manager': {
        'tasks':   (True,  True,  True,  False, 'region'),
        'visits':  (False, True,  False, False, 'region'),
        'reports': (False, True,  False, False, 'region'),
        'logs':    (False, True,  False, False, 'region'),
        'users':   (False, True,  False, False, 'region'),
    },
    'Team Lead': {
        'tasks':   (True,  True,  True,  False, 'team'),
        'visits':  (False, True,  False, False, 'team'),
        'reports': (False, True,  False, False, 'team'),
        'logs':    (False, True,  False, False, 'team'),
        'users':   (False, True,  False, False, 'team'),
    },
    'Field Agent': {
        'tasks':   (False, True,  True,  False, 'own'),
        'visits':  (True,  True,  True,  False, 'own'),
        'reports': (False, False, False, False, 'own'),
        'logs':    (False, False, False, False, 'own'),
        'users':   (False, False, False, False, 'own'),
    },
    'Auditor': {
        'tasks':   (False, True,  False, False, 'all'),
        'visits':  (False, True,  False, False, 'all'),
        'reports': (False, True,  False, False, 'all'),
        'logs':    (False, True,  False, False, 'all'),
        'users':   (False, True,  False, False, 'all'),
    },
}


class Command(BaseCommand):
    help = 'Seeds the database with roles, permissions, regions, teams, and users.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n[SEED]  Starting FieldFlow database seed...\n'))

        with transaction.atomic():
            roles = self._seed_roles()
            self._seed_permissions(roles)
            regions = self._seed_regions(roles)
            teams = self._seed_teams(regions, roles)
            self._seed_users(roles, regions, teams)

        self.stdout.write(self.style.SUCCESS('\n[DONE]  Seed complete!\n'))
        self._print_credentials()

    # ─────────────────────────────────────────────────────────
    # Roles
    # ─────────────────────────────────────────────────────────
    def _seed_roles(self):
        self.stdout.write('  Creating roles...')
        role_definitions = [
            ('Admin', 'Full system access. Can manage all data and users.'),
            ('Regional Manager', 'Manages tasks and agents within their region.'),
            ('Team Lead', 'Assigns tasks and monitors their team.'),
            ('Field Agent', 'Performs visits and updates their own tasks.'),
            ('Auditor', 'Read-only access to reports and activity logs.'),
        ]
        roles = {}
        for name, desc in role_definitions:
            role, created = Role.objects.get_or_create(name=name, defaults={'description': desc})
            roles[name] = role
            status_str = 'created' if created else 'exists'
            self.stdout.write(f'    {status_str}: {name}')
        return roles

    # ─────────────────────────────────────────────────────────
    # Module Permissions
    # ─────────────────────────────────────────────────────────
    def _seed_permissions(self, roles):
        self.stdout.write('  Setting up module permissions...')
        for role_name, modules in PERMISSION_MATRIX.items():
            role = roles[role_name]
            for module, (create, read, update, delete, scope) in modules.items():
                ModulePermission.objects.update_or_create(
                    role=role,
                    module=module,
                    defaults={
                        'can_create': create,
                        'can_read': read,
                        'can_update': update,
                        'can_delete': delete,
                        'scope': scope,
                    }
                )
        self.stdout.write('    [OK] All module permissions set')

    # ─────────────────────────────────────────────────────────
    # Regions
    # ─────────────────────────────────────────────────────────
    def _seed_regions(self, roles):
        self.stdout.write('  Creating regions...')
        region_names = ['North Zone', 'South Zone']
        regions = {}
        for name in region_names:
            region, created = Region.objects.get_or_create(name=name)
            regions[name] = region
            status_str = 'created' if created else 'exists'
            self.stdout.write(f'    {status_str}: {name}')
        return regions

    # ─────────────────────────────────────────────────────────
    # Teams
    # ─────────────────────────────────────────────────────────
    def _seed_teams(self, regions, roles):
        self.stdout.write('  Creating teams...')
        team_definitions = [
            ('Alpha Team', 'North Zone'),
            ('Beta Team', 'North Zone'),
            ('Gamma Team', 'South Zone'),
        ]
        teams = {}
        for name, region_name in team_definitions:
            region = regions[region_name]
            team, created = Team.objects.get_or_create(name=name, region=region)
            teams[name] = team
            status_str = 'created' if created else 'exists'
            self.stdout.write(f'    {status_str}: {name} ({region_name})')
        return teams

    # ─────────────────────────────────────────────────────────
    # Users
    # ─────────────────────────────────────────────────────────
    def _seed_users(self, roles, regions, teams):
        self.stdout.write('  Creating users...')
        users_data = [
            # (username, email, password, first, last, role, region, team, emp_code)
            ('admin', 'admin@fieldflow.com', 'Admin@123',
             'System', 'Admin', 'Admin', None, None, 'EMP001'),

            ('rm_north', 'rm.north@fieldflow.com', 'Pass@123',
             'Rahul', 'Mehta', 'Regional Manager', 'North Zone', None, 'EMP002'),

            ('rm_south', 'rm.south@fieldflow.com', 'Pass@123',
             'Priya', 'Sharma', 'Regional Manager', 'South Zone', None, 'EMP003'),

            ('tl_alpha', 'tl.alpha@fieldflow.com', 'Pass@123',
             'Arjun', 'Singh', 'Team Lead', 'North Zone', 'Alpha Team', 'EMP004'),

            ('tl_beta', 'tl.beta@fieldflow.com', 'Pass@123',
             'Neha', 'Gupta', 'Team Lead', 'North Zone', 'Beta Team', 'EMP005'),

            ('tl_gamma', 'tl.gamma@fieldflow.com', 'Pass@123',
             'Vikram', 'Rao', 'Team Lead', 'South Zone', 'Gamma Team', 'EMP006'),

            ('agent1', 'agent1@fieldflow.com', 'Pass@123',
             'Amit', 'Kumar', 'Field Agent', 'North Zone', 'Alpha Team', 'EMP007'),

            ('agent2', 'agent2@fieldflow.com', 'Pass@123',
             'Sita', 'Devi', 'Field Agent', 'North Zone', 'Alpha Team', 'EMP008'),

            ('agent3', 'agent3@fieldflow.com', 'Pass@123',
             'Ravi', 'Verma', 'Field Agent', 'North Zone', 'Beta Team', 'EMP009'),

            ('agent4', 'agent4@fieldflow.com', 'Pass@123',
             'Meena', 'Patel', 'Field Agent', 'South Zone', 'Gamma Team', 'EMP010'),

            ('agent5', 'agent5@fieldflow.com', 'Pass@123',
             'Suresh', 'Nair', 'Field Agent', 'South Zone', 'Gamma Team', 'EMP011'),

            ('auditor', 'auditor@fieldflow.com', 'Pass@123',
             'Deepa', 'Iyer', 'Auditor', None, None, 'EMP012'),
        ]

        for (username, email, password, first, last,
             role_name, region_name, team_name, emp_code) in users_data:

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': first,
                    'last_name': last,
                    'role': roles[role_name],
                    'region': regions.get(region_name) if region_name else None,
                    'team': teams.get(team_name) if team_name else None,
                    'is_staff': role_name == 'Admin',
                    'is_superuser': role_name == 'Admin',
                }
            )
            if created:
                user.set_password(password)
                user.save()

            EmployeeProfile.objects.get_or_create(
                user=user,
                defaults={'employee_code': emp_code}
            )

            status_str = 'created' if created else 'exists'
            self.stdout.write(f'    {status_str}: {email} [{role_name}]')

        # Assign managers and leads
        self._assign_managers(regions, teams)

    def _assign_managers(self, regions, teams):
        """Link region managers and team leads after all users exist."""
        try:
            regions['North Zone'].manager = User.objects.get(email='rm.north@fieldflow.com')
            regions['North Zone'].save()
            regions['South Zone'].manager = User.objects.get(email='rm.south@fieldflow.com')
            regions['South Zone'].save()

            teams['Alpha Team'].lead = User.objects.get(email='tl.alpha@fieldflow.com')
            teams['Alpha Team'].save()
            teams['Beta Team'].lead = User.objects.get(email='tl.beta@fieldflow.com')
            teams['Beta Team'].save()
            teams['Gamma Team'].lead = User.objects.get(email='tl.gamma@fieldflow.com')
            teams['Gamma Team'].save()
        except User.DoesNotExist:
            pass

    # ---------------------------------------------------------
    # Credentials Summary
    # ---------------------------------------------------------
    def _print_credentials(self):
        sep = '-' * 60
        self.stdout.write(self.style.MIGRATE_HEADING(sep))
        self.stdout.write(self.style.MIGRATE_HEADING('  SEEDED CREDENTIALS'))
        self.stdout.write(self.style.MIGRATE_HEADING(sep))
        credentials = [
            ('Admin',            'admin@fieldflow.com',    'Admin@123'),
            ('Regional Manager', 'rm.north@fieldflow.com', 'Pass@123'),
            ('Regional Manager', 'rm.south@fieldflow.com', 'Pass@123'),
            ('Team Lead',        'tl.alpha@fieldflow.com', 'Pass@123'),
            ('Team Lead',        'tl.beta@fieldflow.com',  'Pass@123'),
            ('Team Lead',        'tl.gamma@fieldflow.com', 'Pass@123'),
            ('Field Agent',      'agent1@fieldflow.com',   'Pass@123'),
            ('Field Agent',      'agent2@fieldflow.com',   'Pass@123'),
            ('Field Agent',      'agent3@fieldflow.com',   'Pass@123'),
            ('Field Agent',      'agent4@fieldflow.com',   'Pass@123'),
            ('Field Agent',      'agent5@fieldflow.com',   'Pass@123'),
            ('Auditor',          'auditor@fieldflow.com',  'Pass@123'),
        ]
        self.stdout.write(f"  {'Role':<20} {'Email':<35} {'Password'}")
        self.stdout.write('  ' + '-' * 56)
        for role, email, pwd in credentials:
            self.stdout.write(f"  {role:<20} {email:<35} {pwd}")
        self.stdout.write(self.style.MIGRATE_HEADING(sep + '\n'))
