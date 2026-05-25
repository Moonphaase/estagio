import os
import tempfile
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from categories.models import Category
from datasets.models import Dataset, DatasetVersion

User = get_user_model()


class DatasetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@test.com', username='admin', password='admin1234'
        )
        self.user = User.objects.create_user(
            email='user@test.com', username='user', password='user1234'
        )
        self.other = User.objects.create_user(
            email='other@test.com', username='other', password='other1234'
        )
        self.category = Category.objects.create(name='Saúde')
        self.dataset = Dataset.objects.create(
            name='Dataset Teste',
            owner=self.user,
            visibility='public',
            status='published',
            category=self.category,
        )
        self.private_dataset = Dataset.objects.create(
            name='Dataset Privado',
            owner=self.user,
            visibility='private',
            status='published',
        )

    # ── Listagem ──────────────────────────────────────────────────────────────

    def test_listar_datasets_publicos_guest(self):
        res = self.client.get('/api/datasets/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        nomes = [d['name'] for d in res.data['results']]
        self.assertIn('Dataset Teste', nomes)
        self.assertNotIn('Dataset Privado', nomes)

    def test_listar_datasets_dono_ve_privados(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/datasets/')
        nomes = [d['name'] for d in res.data['results']]
        self.assertIn('Dataset Privado', nomes)

    def test_outro_utilizador_nao_ve_privados(self):
        self.client.force_authenticate(user=self.other)
        res = self.client.get('/api/datasets/')
        nomes = [d['name'] for d in res.data['results']]
        self.assertNotIn('Dataset Privado', nomes)

    def test_admin_ve_tudo(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/datasets/')
        nomes = [d['name'] for d in res.data['results']]
        self.assertIn('Dataset Privado', nomes)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def test_criar_dataset_autenticado(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/api/datasets/', {
            'name': 'Novo Dataset',
            'visibility': 'public',
            'status': 'draft',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name'], 'Novo Dataset')

    def test_criar_dataset_guest(self):
        res = self.client.post('/api/datasets/', {'name': 'Teste'})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_editar_dataset_dono(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(f'/api/datasets/{self.dataset.id}/', {'name': 'Editado'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'Editado')

    def test_editar_dataset_outro_utilizador(self):
        self.client.force_authenticate(user=self.other)
        res = self.client.patch(f'/api/datasets/{self.dataset.id}/', {'name': 'Hack'})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_apagar_dataset_dono(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.delete(f'/api/datasets/{self.dataset.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_apagar_dataset_outro_utilizador(self):
        self.client.force_authenticate(user=self.other)
        res = self.client.delete(f'/api/datasets/{self.dataset.id}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_slug_gerado_automaticamente(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/api/datasets/', {
            'name': 'Dataset Com Slug',
            'visibility': 'public',
            'status': 'draft',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['slug'], 'dataset-com-slug')


class DatasetVersionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@test.com', username='user', password='user1234'
        )
        self.other = User.objects.create_user(
            email='other@test.com', username='other', password='other1234'
        )
        self.dataset = Dataset.objects.create(
            name='Dataset Teste',
            owner=self.user,
            visibility='public',
            status='published',
        )

    def _csv_file(self, name='test.csv'):
        return SimpleUploadedFile(name, b'col1,col2\n1,2\n3,4', content_type='text/csv')

    def test_criar_versao_dono(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post(
            f'/api/datasets/{self.dataset.id}/versions/',
            {'version': '1.0.0', 'file': self._csv_file()},
            format='multipart'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['is_latest'])

    def test_criar_versao_outro_utilizador(self):
        self.client.force_authenticate(user=self.other)
        res = self.client.post(
            f'/api/datasets/{self.dataset.id}/versions/',
            {'version': '1.0.0', 'file': self._csv_file()},
            format='multipart'
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_is_latest_atualizado(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(
            f'/api/datasets/{self.dataset.id}/versions/',
            {'version': '1.0.0', 'file': self._csv_file('v1.csv')},
            format='multipart'
        )
        self.client.post(
            f'/api/datasets/{self.dataset.id}/versions/',
            {'version': '2.0.0', 'file': self._csv_file('v2.csv')},
            format='multipart'
        )
        versions = DatasetVersion.objects.filter(dataset=self.dataset)
        latest = versions.filter(is_latest=True)
        self.assertEqual(latest.count(), 1)
        self.assertEqual(latest.first().version, '2.0.0')

    def test_versao_duplicada(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(
            f'/api/datasets/{self.dataset.id}/versions/',
            {'version': '1.0.0', 'file': self._csv_file('v1a.csv')},
            format='multipart'
        )
        res = self.client.post(
            f'/api/datasets/{self.dataset.id}/versions/',
            {'version': '1.0.0', 'file': self._csv_file('v1b.csv')},
            format='multipart'
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_checksum_preenchido(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post(
            f'/api/datasets/{self.dataset.id}/versions/',
            {'version': '1.0.0', 'file': self._csv_file()},
            format='multipart'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        version = DatasetVersion.objects.get(id=res.data['id'])
        self.assertNotEqual(version.checksum, '')