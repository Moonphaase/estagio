from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from categories.models import Category

User = get_user_model()


class CategoryTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@test.com', username='admin', password='admin1234'
        )
        self.user = User.objects.create_user(
            email='user@test.com', username='user', password='user1234'
        )
        self.category = Category.objects.create(name='Saúde', description='Dados de saúde')

    def test_listar_categorias_autenticado(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/categories/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_criar_categoria_admin(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/categories/', {
            'name': 'Finanças',
            'description': 'Dados financeiros'
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name'], 'Finanças')

    def test_criar_categoria_utilizador_normal(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/api/categories/', {
            'name': 'Ambiente',
            'description': 'Dados ambientais'
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_slug_gerado_automaticamente(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/categories/', {'name': 'Transportes'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['slug'], 'transportes')

    def test_apagar_categoria_admin(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(f'/api/categories/{self.category.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_apagar_categoria_utilizador_normal(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.delete(f'/api/categories/{self.category.id}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)