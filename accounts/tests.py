from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class AuthTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@test.com', username='admin', password='admin1234'
        )
        self.user = User.objects.create_user(
            email='user@test.com', username='user', password='user1234'
        )

    def test_login_com_email_correto(self):
        res = self.client.post('/api/auth/login/', {
            'email': 'user@test.com',
            'password': 'user1234'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_login_com_password_errada(self):
        res = self.client.post('/api/auth/login/', {
            'email': 'user@test.com',
            'password': 'errada'
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_autenticado(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], 'user@test.com')

    def test_me_nao_autenticado(self):
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_so_admin(self):
        # Utilizador normal não pode registar
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/register/', {
            'username': 'novo',
            'email': 'novo@test.com',
            'password': 'nova1234'
        })
        self.assertNotEqual(res.status_code, status.HTTP_201_CREATED)

    def test_logout_blacklist(self):
        res = self.client.post('/api/auth/login/', {
            'email': 'user@test.com',
            'password': 'user1234'
        })
        refresh = res.data['refresh']
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/api/auth/logout/', {'refresh': refresh})
        self.assertEqual(res.status_code, status.HTTP_200_OK)