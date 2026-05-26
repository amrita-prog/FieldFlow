from django.contrib import admin
from visits.models import Visit, AIOutput


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['location', 'agent', 'task', 'status', 'outcome', 'started_at', 'completed_at']
    list_filter = ['status', 'outcome']
    search_fields = ['location', 'notes', 'agent__email']
    ordering = ['-created_at']


@admin.register(AIOutput)
class AIOutputAdmin(admin.ModelAdmin):
    list_display = ['visit', 'risk_flag', 'generated_at']
    list_filter = ['risk_flag']
    ordering = ['-generated_at']
