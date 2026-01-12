"""
Tests for ownership tracking and multi-tenant isolation.
"""
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, AuthenticationProfile

User = get_user_model()


class OwnershipTests(TestCase):
    """Tests for ownership tracking and multi-tenant isolation."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='pass1')
        self.user2 = User.objects.create_user(username='user2', password='pass2')
        self.admin = User.objects.create_superuser(username='admin', password='admin')
        self.api_base = '/_mokkapi_api/api'

    # --- Endpoint Ownership ---
    def test_endpoint_creator_set_on_create(self):
        """creator field is set to current user on create."""
        self.client.login(username='user1', password='pass1')
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/creator-test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        endpoint = MockEndpoint.objects.get(path='api/creator-test')
        self.assertEqual(endpoint.creator.id, self.user1.id)

    def test_endpoint_owner_set_on_create(self):
        """owner field is set to current user on create."""
        self.client.login(username='user1', password='pass1')
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/owner-test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        endpoint = MockEndpoint.objects.get(path='api/owner-test')
        self.assertEqual(endpoint.owner.id, self.user1.id)

    def test_user_sees_only_own_endpoints(self):
        """User list view only shows their endpoints."""
        MockEndpoint.objects.create(
            path='api/user1-endpoint',
            owner=self.user1,
            creator=self.user1
        )
        MockEndpoint.objects.create(
            path='api/user2-endpoint',
            owner=self.user2,
            creator=self.user2
        )

        self.client.login(username='user1', password='pass1')
        response = self.client.get(f'{self.api_base}/endpoints/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        paths = [e['path'] for e in data]
        self.assertIn('api/user1-endpoint', paths)
        self.assertNotIn('api/user2-endpoint', paths)

    def test_user_cannot_access_others_endpoint(self):
        """User cannot GET another user's endpoint."""
        other_endpoint = MockEndpoint.objects.create(
            path='api/user2-private',
            owner=self.user2,
            creator=self.user2
        )
        self.client.login(username='user1', password='pass1')
        response = self.client.get(f'{self.api_base}/endpoints/{other_endpoint.id}/')
        self.assertIn(response.status_code, [403, 404])

    def test_user_cannot_update_others_endpoint(self):
        """User cannot PUT/PATCH another user's endpoint."""
        other_endpoint = MockEndpoint.objects.create(
            path='api/user2-update',
            owner=self.user2,
            creator=self.user2
        )
        self.client.login(username='user1', password='pass1')
        response = self.client.patch(
            f'{self.api_base}/endpoints/{other_endpoint.id}/',
            data=json.dumps({'description': 'Hacked'}),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [403, 404])

    def test_user_cannot_delete_others_endpoint(self):
        """User cannot DELETE another user's endpoint."""
        other_endpoint = MockEndpoint.objects.create(
            path='api/user2-delete',
            owner=self.user2,
            creator=self.user2
        )
        self.client.login(username='user1', password='pass1')
        response = self.client.delete(f'{self.api_base}/endpoints/{other_endpoint.id}/')
        self.assertIn(response.status_code, [403, 404])
        self.assertTrue(MockEndpoint.objects.filter(id=other_endpoint.id).exists())

    # --- Admin Access ---
    def test_admin_sees_all_endpoints(self):
        """Admin can list all endpoints from all users."""
        MockEndpoint.objects.create(
            path='api/user1-admin-test',
            owner=self.user1,
            creator=self.user1
        )
        MockEndpoint.objects.create(
            path='api/user2-admin-test',
            owner=self.user2,
            creator=self.user2
        )

        self.client.login(username='admin', password='admin')
        response = self.client.get(f'{self.api_base}/endpoints/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 2)

    def test_admin_can_access_any_endpoint(self):
        """Admin can access any user's endpoint."""
        user_endpoint = MockEndpoint.objects.create(
            path='api/user-for-admin',
            owner=self.user1,
            creator=self.user1
        )
        self.client.login(username='admin', password='admin')
        response = self.client.get(f'{self.api_base}/endpoints/{user_endpoint.id}/')
        self.assertEqual(response.status_code, 200)

    def test_admin_can_modify_any_endpoint(self):
        """Admin can update/delete any user's endpoint."""
        user_endpoint = MockEndpoint.objects.create(
            path='api/admin-modify',
            owner=self.user1,
            creator=self.user1
        )
        self.client.login(username='admin', password='admin')
        response = self.client.patch(
            f'{self.api_base}/endpoints/{user_endpoint.id}/',
            data=json.dumps({'description': 'Admin updated'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    # --- Auth Profile Ownership ---
    def test_auth_profile_owner_set_on_create(self):
        """Auth profile owner is set on create."""
        self.client.login(username='user1', password='pass1')
        response = self.client.post(
            f'{self.api_base}/auth-profiles/',
            data=json.dumps({
                'name': 'My Profile',
                'auth_type': 'API_KEY'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        profile = AuthenticationProfile.objects.get(name='My Profile')
        self.assertEqual(profile.owner.id, self.user1.id)

    def test_user_sees_only_own_auth_profiles(self):
        """User list only shows their auth profiles."""
        AuthenticationProfile.objects.create(
            name='User1 Profile',
            auth_type='API_KEY',
            api_key='key1',
            owner=self.user1
        )
        AuthenticationProfile.objects.create(
            name='User2 Profile',
            auth_type='API_KEY',
            api_key='key2',
            owner=self.user2
        )

        self.client.login(username='user1', password='pass1')
        response = self.client.get(f'{self.api_base}/auth-profiles/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        names = [p['name'] for p in data]
        self.assertIn('User1 Profile', names)
        self.assertNotIn('User2 Profile', names)

    def test_user_cannot_use_others_auth_profile(self):
        """User cannot attach another user's auth profile to endpoint."""
        other_profile = AuthenticationProfile.objects.create(
            name='Other User Profile',
            auth_type='API_KEY',
            api_key='other-key',
            owner=self.user2
        )
        self.client.login(username='user1', password='pass1')
        my_endpoint = MockEndpoint.objects.create(
            path='api/my-endpoint',
            owner=self.user1,
            creator=self.user1
        )
        response = self.client.patch(
            f'{self.api_base}/endpoints/{my_endpoint.id}/',
            data=json.dumps({'authentication': other_profile.id}),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [400, 403])
