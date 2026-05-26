"""
logs/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from logs.views import ActivityLogViewSet

router = DefaultRouter()
router.register(r'logs', ActivityLogViewSet, basename='log')

urlpatterns = [
    path('', include(router.urls)),
]
