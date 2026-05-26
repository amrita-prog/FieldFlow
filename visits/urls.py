"""
visits/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from visits.views import VisitViewSet

router = DefaultRouter()
router.register(r'visits', VisitViewSet, basename='visit')

urlpatterns = [
    path('', include(router.urls)),
]
