from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.permissions import AllowAny

from .serializers import RegisterSerializer, UserSerializer, EmailTokenObtainPairSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/"""
    queryset           = User.objects.all()
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user":    UserSerializer(user).data,
            "refresh": str(refresh),
            "access":  str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/  (email + password → access + refresh)"""
    serializer_class   = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class TokenRefreshView(TokenRefreshView):
    """POST /api/auth/token/refresh/"""
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    """POST /api/auth/logout/  — blacklist do refresh token"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout efetuado com sucesso."})
        except Exception:
            return Response(
                {"detail": "Token inválido ou já expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/"""
    serializer_class   = UserSerializer
    # Garante que este endpoint exige autenticação.
    # Se estiveres a usar a API Key, ela será validada aqui.
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    
class DebugHeadersView(APIView):
    """GET /api/auth/debug-headers/ — temporário, para diagnóstico"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "HTTP_AUTHORIZATION": request.META.get('HTTP_AUTHORIZATION'),
            "all_http_headers": {k: v for k, v in request.META.items() if k.startswith('HTTP_')},
        })