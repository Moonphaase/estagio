from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import APIKey
from .serializers import APIKeyCreateSerializer, APIKeyListSerializer


class APIKeyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keys = APIKey.objects.filter(user=request.user)
        serializer = APIKeyListSerializer(keys, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance, raw_key = APIKey.generate(
            user=request.user,
            name=serializer.validated_data['name'],
            permissions=serializer.validated_data.get('permissions', 'read'),
            expires_at=serializer.validated_data.get('expires_at'),
        )

        return Response({
            'id': instance.id,
            'name': instance.name,
            'key': raw_key,        # ← mostrado UMA SÓ VEZ
            'prefix': instance.key_prefix,
            'permissions': instance.permissions,
            'message': 'Guarda esta chave agora. Não será mostrada novamente.',
        }, status=status.HTTP_201_CREATED)


class APIKeyRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            key = APIKey.objects.get(pk=pk, user=request.user)
        except APIKey.DoesNotExist:
            return Response({'detail': 'Não encontrada.'}, status=404)
        key.is_active = False
        key.save(update_fields=['is_active'])
        return Response({'detail': 'API Key revogada.'})