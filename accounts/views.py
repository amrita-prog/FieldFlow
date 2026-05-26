"""
accounts/views.py

Authentication views and user management viewset.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.models import User, ModulePermission
from accounts.serializers import (
    LoginSerializer,
    UserDetailSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserBriefSerializer,
)
from accounts.permissions import IsAdminRole


# ─────────────────────────────────────────────────────────────
# Helper: build token pair for a user
# ─────────────────────────────────────────────────────────────

def _get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# ─────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────

class LoginView(APIView):
    """
    POST /api/auth/login/
    Public endpoint. Returns JWT pair + full user profile + permissions.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        tokens = _get_tokens_for_user(user)
        user_data = UserDetailSerializer(user).data

        # Log the login action (import here to avoid circular; logs app built later)
        try:
            from logs.utils import log_activity
            log_activity(user, 'user_logged_in', user)
        except Exception:
            pass

        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': user_data,
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklists the refresh token so it cannot be used again.
    Body: { "refresh": "<refresh_token>" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': True, 'code': 'BAD_REQUEST', 'message': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {'error': True, 'code': 'BAD_REQUEST', 'message': 'Token is invalid or already blacklisted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from logs.utils import log_activity
            log_activity(request.user, 'user_logged_out', request.user)
        except Exception:
            pass

        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# Me (Current User Profile)
# ─────────────────────────────────────────────────────────────

class MeView(APIView):
    """
    GET /api/auth/me/
    Returns the authenticated user's full profile, role, and permissions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# User Management (Admin only)
# ─────────────────────────────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    """
    /api/users/
    Admin-only CRUD for user management.
    Destroy is overridden to soft-delete (set is_active=False).
    """
    module = 'users'
    queryset = User.objects.select_related('role', 'region', 'team').all()
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        if self.action == 'list':
            return UserBriefSerializer
        return UserDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Optional filters via query params
        role_name = self.request.query_params.get('role')
        if role_name:
            qs = qs.filter(role__name=role_name)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs

    def destroy(self, request, *args, **kwargs):
        """Soft delete — deactivate instead of delete."""
        user = self.get_object()
        if user == request.user:
            return Response(
                {'error': True, 'code': 'SELF_DELETE', 'message': 'You cannot deactivate your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'message': f'User {user.email} has been deactivated.'}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserDetailSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )
