"""
backend/urls.py  —  Root URL configuration for FieldFlow.

All API routes are prefixed with /api/.
Each app's urls.py is included here as phases are completed.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Phase 1: Auth & Users ──────────────────────────────
    path('api/', include('accounts.urls')),

    # ── Phase 2: Tasks ────────────────────────────────────
    path('api/', include('tasks.urls')),

    # ── Phase 3: Visits ───────────────────────────────────
    path('api/', include('visits.urls')),

    # ── Phase 4: Reports ──────────────────────────────────
    path('api/', include('reports.urls')),

    # ── Phase 5: Logs ─────────────────────────────────────
    path('api/', include('logs.urls')),
]
