"""
accounts/urls.py

Auth endpoints and user management routes.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import LoginView, LogoutView, MeView, UserViewSet

# Router for UserViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Auth
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', MeView.as_view(), name='auth-me'),

    # User management (Admin only)
    path('', include(router.urls)),
]
