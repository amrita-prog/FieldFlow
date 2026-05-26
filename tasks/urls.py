"""
tasks/urls.py

Router for TaskViewSet. The custom actions (assign, status)
are registered automatically via @action decorators.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tasks.views import TaskViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]
