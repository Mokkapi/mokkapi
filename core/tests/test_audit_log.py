"""
Tests for AuditLog model and audit logging functionality.
"""
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler, AuthenticationProfile, AuditLog

User = get_user_model()


class AuditLogModelTests(TestCase):
    """Tests for AuditLog model validation and behavior."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    # --- Model Fields ---
    def test_audit_log_has_required_fields(self):
        """AuditLog model has user, action, endpoint_id, timestamp, old_value, new_value."""
        field_names = [f.name for f in AuditLog._meta.get_fields()]
        self.assertIn('user', field_names)
        self.assertIn('action', field_names)
        self.assertIn('endpoint_id', field_names)
        self.assertIn('timestamp', field_names)
        self.assertIn('old_value', field_names)
        self.assertIn('new_value', field_names)

    def test_timestamp_auto_set_on_create(self):
        """Timestamp is automatically set when audit log is created."""
        from django.utils import timezone
        before = timezone.now()
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            endpoint_id=1
        )
        after = timezone.now()
        self.assertIsNotNone(log.timestamp)
        self.assertGreaterEqual(log.timestamp, before)
        self.assertLessEqual(log.timestamp, after)

    def test_user_can_be_null_for_anonymous(self):
        """User field can be null for anonymous/unauthenticated actions."""
        log = AuditLog.objects.create(
            user=None,
            action='AUTH_FAILURE',
            endpoint_id=1
        )
        self.assertIsNone(log.user)

    def test_endpoint_id_can_be_null(self):
        """endpoint_id can be null for non-endpoint actions."""
        log = AuditLog.objects.create(
            user=self.user,
            action='LOGIN',
            endpoint_id=None
        )
        self.assertIsNone(log.endpoint_id)

    def test_old_value_stores_json(self):
        """old_value field stores JSON representation of previous state."""
        old_data = {'path': 'api/test', 'description': 'Old desc'}
        log = AuditLog.objects.create(
            user=self.user,
            action='UPDATE',
            endpoint_id=1,
            old_value=old_data
        )
        log.refresh_from_db()
        self.assertEqual(log.old_value, old_data)

    def test_new_value_stores_json(self):
        """new_value field stores JSON representation of new state."""
        new_data = {'path': 'api/test', 'description': 'New desc'}
        log = AuditLog.objects.create(
            user=self.user,
            action='UPDATE',
            endpoint_id=1,
            new_value=new_data
        )
        log.refresh_from_db()
        self.assertEqual(log.new_value, new_data)

    def test_old_value_can_be_null(self):
        """old_value can be null for create actions."""
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            endpoint_id=1,
            old_value=None,
            new_value={'path': 'api/new'}
        )
        self.assertIsNone(log.old_value)

    def test_new_value_can_be_null(self):
        """new_value can be null for delete actions."""
        log = AuditLog.objects.create(
            user=self.user,
            action='DELETE',
            endpoint_id=1,
            old_value={'path': 'api/deleted'},
            new_value=None
        )
        self.assertIsNone(log.new_value)

    # --- Action Types ---
    def test_action_choices_include_crud(self):
        """Action field supports CREATE, READ, UPDATE, DELETE."""
        for action in ['CREATE', 'READ', 'UPDATE', 'DELETE']:
            log = AuditLog(user=self.user, action=action)
            log.full_clean()

    def test_action_choices_include_auth_actions(self):
        """Action field supports LOGIN, LOGOUT, AUTH_FAILURE."""
        for action in ['LOGIN', 'LOGOUT', 'AUTH_FAILURE']:
            log = AuditLog(user=self.user, action=action)
            log.full_clean()

    def test_action_choices_include_permission_denied(self):
        """Action field supports PERMISSION_DENIED."""
        log = AuditLog(user=self.user, action='PERMISSION_DENIED')
        log.full_clean()

    # --- String Representation ---
    def test_str_method_includes_action_and_user(self):
        """__str__ includes action type and username."""
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            endpoint_id=1
        )
        str_repr = str(log)
        self.assertIn('CREATE', str_repr)
        self.assertIn('testuser', str_repr)

    def test_str_method_handles_anonymous_user(self):
        """__str__ handles null user gracefully."""
        log = AuditLog.objects.create(
            user=None,
            action='AUTH_FAILURE',
            endpoint_id=1
        )
        str_repr = str(log)
        self.assertIn('AUTH_FAILURE', str_repr)


class AuditLogEndpointCRUDTests(TestCase):
    """Tests for audit logging of MockEndpoint CRUD operations."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.api_base = '/_mokkapi_api/api'

    # --- Create Endpoint ---
    def test_endpoint_create_logged(self):
        """Creating an endpoint creates an audit log entry."""
        initial_count = AuditLog.objects.count()
        self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/audit-create'}),
            content_type='application/json'
        )
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)

    def test_endpoint_create_log_has_correct_action(self):
        """Endpoint create audit log has action='CREATE'."""
        self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/audit-action'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.action, 'CREATE')

    def test_endpoint_create_log_has_user(self):
        """Endpoint create audit log records the user."""
        self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/audit-user'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.user.id, self.user.id)

    def test_endpoint_create_log_has_endpoint_id(self):
        """Endpoint create audit log records the new endpoint_id."""
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/audit-endpoint-id'}),
            content_type='application/json'
        )
        endpoint_id = response.json()['id']
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.endpoint_id, endpoint_id)

    def test_endpoint_create_log_old_value_is_null(self):
        """Endpoint create audit log has null old_value."""
        self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/audit-old-null'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertIsNone(log.old_value)

    def test_endpoint_create_log_new_value_has_data(self):
        """Endpoint create audit log new_value contains endpoint data."""
        self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/audit-new-value'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertIsNotNone(log.new_value)
        self.assertIn('path', log.new_value)

    # --- Read/Retrieve Endpoint ---
    def test_endpoint_retrieve_logged(self):
        """Retrieving an endpoint detail creates an audit log entry."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-retrieve',
            owner=self.user,
            creator=self.user
        )
        initial_count = AuditLog.objects.count()
        self.client.get(f'{self.api_base}/endpoints/{endpoint.id}/')
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_endpoint_list_logged(self):
        """Listing endpoints creates an audit log entry."""
        initial_count = AuditLog.objects.count()
        self.client.get(f'{self.api_base}/endpoints/')
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_endpoint_read_log_has_correct_action(self):
        """Endpoint read audit log has action='READ'."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-read-action',
            owner=self.user,
            creator=self.user
        )
        self.client.get(f'{self.api_base}/endpoints/{endpoint.id}/')
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.action, 'READ')

    # --- Update Endpoint ---
    def test_endpoint_update_logged(self):
        """Updating an endpoint creates an audit log entry."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-update',
            owner=self.user,
            creator=self.user
        )
        initial_count = AuditLog.objects.count()
        self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps({'description': 'Updated'}),
            content_type='application/json'
        )
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_endpoint_update_log_has_correct_action(self):
        """Endpoint update audit log has action='UPDATE'."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-update-action',
            owner=self.user,
            creator=self.user
        )
        self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps({'description': 'Updated'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.action, 'UPDATE')

    def test_endpoint_update_log_has_old_value(self):
        """Endpoint update audit log contains previous state in old_value."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-update-old',
            owner=self.user,
            creator=self.user,
            description='Original'
        )
        self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps({'description': 'Updated'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertIsNotNone(log.old_value)
        self.assertEqual(log.old_value.get('description'), 'Original')

    def test_endpoint_update_log_has_new_value(self):
        """Endpoint update audit log contains new state in new_value."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-update-new',
            owner=self.user,
            creator=self.user,
            description='Original'
        )
        self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps({'description': 'Updated'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertIsNotNone(log.new_value)
        self.assertEqual(log.new_value.get('description'), 'Updated')

    # --- Delete Endpoint ---
    def test_endpoint_delete_logged(self):
        """Deleting an endpoint creates an audit log entry."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-delete',
            owner=self.user,
            creator=self.user
        )
        initial_count = AuditLog.objects.count()
        self.client.delete(f'{self.api_base}/endpoints/{endpoint.id}/')
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_endpoint_delete_log_has_correct_action(self):
        """Endpoint delete audit log has action='DELETE'."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-delete-action',
            owner=self.user,
            creator=self.user
        )
        self.client.delete(f'{self.api_base}/endpoints/{endpoint.id}/')
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.action, 'DELETE')

    def test_endpoint_delete_log_has_old_value(self):
        """Endpoint delete audit log contains deleted data in old_value."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-delete-old',
            owner=self.user,
            creator=self.user
        )
        self.client.delete(f'{self.api_base}/endpoints/{endpoint.id}/')
        log = AuditLog.objects.latest('timestamp')
        self.assertIsNotNone(log.old_value)
        self.assertEqual(log.old_value.get('path'), 'api/audit-delete-old')

    def test_endpoint_delete_log_new_value_is_null(self):
        """Endpoint delete audit log has null new_value."""
        endpoint = MockEndpoint.objects.create(
            path='api/audit-delete-null',
            owner=self.user,
            creator=self.user
        )
        self.client.delete(f'{self.api_base}/endpoints/{endpoint.id}/')
        log = AuditLog.objects.latest('timestamp')
        self.assertIsNone(log.new_value)


class AuditLogHandlerCRUDTests(TestCase):
    """Tests for audit logging of ResponseHandler CRUD operations."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.api_base = '/_mokkapi_api/api'
        self.endpoint = MockEndpoint.objects.create(
            path="test/audit-handlers",
            owner=self.user,
            creator=self.user
        )

    # --- Create Handler ---
    def test_handler_create_logged(self):
        """Creating a handler creates an audit log entry."""
        initial_count = AuditLog.objects.count()
        self.client.post(
            f'{self.api_base}/handlers/',
            data=json.dumps({
                'endpoint': self.endpoint.id,
                'http_method': 'GET',
                'response_status_code': 200
            }),
            content_type='application/json'
        )
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_handler_create_log_includes_endpoint_id(self):
        """Handler create audit log includes parent endpoint_id."""
        self.client.post(
            f'{self.api_base}/handlers/',
            data=json.dumps({
                'endpoint': self.endpoint.id,
                'http_method': 'POST',
                'response_status_code': 201
            }),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.endpoint_id, self.endpoint.id)

    # --- Update Handler ---
    def test_handler_update_logged(self):
        """Updating a handler creates an audit log entry."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method='GET',
            response_status_code=200
        )
        initial_count = AuditLog.objects.count()
        self.client.patch(
            f'{self.api_base}/handlers/{handler.id}/',
            data=json.dumps({'response_status_code': 201}),
            content_type='application/json'
        )
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_handler_update_log_captures_body_change(self):
        """Handler update audit log captures response_body changes."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"old": true}'
        )
        self.client.patch(
            f'{self.api_base}/handlers/{handler.id}/',
            data=json.dumps({'response_body': '{"new": true}'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.old_value.get('response_body'), '{"old": true}')
        self.assertEqual(log.new_value.get('response_body'), '{"new": true}')

    # --- Delete Handler ---
    def test_handler_delete_logged(self):
        """Deleting a handler creates an audit log entry."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method='DELETE',
            response_status_code=204
        )
        initial_count = AuditLog.objects.count()
        self.client.delete(f'{self.api_base}/handlers/{handler.id}/')
        self.assertGreater(AuditLog.objects.count(), initial_count)


class AuditLogAuthProfileCRUDTests(TestCase):
    """Tests for audit logging of AuthenticationProfile CRUD operations."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.api_base = '/_mokkapi_api/api'

    # --- Create Auth Profile ---
    def test_auth_profile_create_logged(self):
        """Creating an auth profile creates an audit log entry."""
        initial_count = AuditLog.objects.count()
        self.client.post(
            f'{self.api_base}/auth-profiles/',
            data=json.dumps({'name': 'Test Profile', 'auth_type': 'api_key'}),
            content_type='application/json'
        )
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_auth_profile_create_log_excludes_secrets(self):
        """Auth profile create log does NOT include api_key or password."""
        self.client.post(
            f'{self.api_base}/auth-profiles/',
            data=json.dumps({'name': 'Secret Profile', 'auth_type': 'api_key'}),
            content_type='application/json'
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertNotIn('api_key', log.new_value)
        self.assertNotIn('password', log.new_value)

    # --- Update Auth Profile ---
    def test_auth_profile_update_logged(self):
        """Updating an auth profile creates an audit log entry."""
        profile = AuthenticationProfile.objects.create(
            name='Update Test',
            auth_type='api_key',
            api_key='test-key',
            owner=self.user
        )
        initial_count = AuditLog.objects.count()
        self.client.patch(
            f'{self.api_base}/auth-profiles/{profile.id}/',
            data=json.dumps({'name': 'Updated Name'}),
            content_type='application/json'
        )
        self.assertGreater(AuditLog.objects.count(), initial_count)

    # --- Delete Auth Profile ---
    def test_auth_profile_delete_logged(self):
        """Deleting an auth profile creates an audit log entry."""
        profile = AuthenticationProfile.objects.create(
            name='Delete Test',
            auth_type='api_key',
            api_key='delete-key',
            owner=self.user
        )
        initial_count = AuditLog.objects.count()
        self.client.delete(f'{self.api_base}/auth-profiles/{profile.id}/')
        self.assertGreater(AuditLog.objects.count(), initial_count)


class AuditLogPermissionDenialTests(TestCase):
    """Tests for audit logging of permission denials."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='pass1')
        self.user2 = User.objects.create_user(username='user2', password='pass2')
        self.api_base = '/_mokkapi_api/api'
        self.endpoint = MockEndpoint.objects.create(
            path="test/audit-permissions",
            owner=self.user1,
            creator=self.user1
        )

    # --- Endpoint Permission Denials ---
    def test_unauthorized_endpoint_access_logged(self):
        """Attempt to access another user's endpoint is logged."""
        self.client.login(username='user2', password='pass2')
        initial_count = AuditLog.objects.count()
        self.client.get(f'{self.api_base}/endpoints/{self.endpoint.id}/')
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_unauthorized_endpoint_update_logged(self):
        """Attempt to update another user's endpoint is logged."""
        self.client.login(username='user2', password='pass2')
        initial_count = AuditLog.objects.count()
        self.client.patch(
            f'{self.api_base}/endpoints/{self.endpoint.id}/',
            data=json.dumps({'description': 'Hacked'}),
            content_type='application/json'
        )
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_permission_denial_log_has_correct_action(self):
        """Permission denial audit log has action='PERMISSION_DENIED'."""
        self.client.login(username='user2', password='pass2')
        self.client.get(f'{self.api_base}/endpoints/{self.endpoint.id}/')
        log = AuditLog.objects.filter(action='PERMISSION_DENIED').latest('timestamp')
        self.assertEqual(log.action, 'PERMISSION_DENIED')

    # --- Unauthenticated Access ---
    def test_unauthenticated_api_access_logged(self):
        """Unauthenticated attempt to access protected API is logged."""
        self.client.logout()
        initial_count = AuditLog.objects.count()
        self.client.get(f'{self.api_base}/endpoints/')
        self.assertGreater(AuditLog.objects.count(), initial_count)


class AuditLogMockAccessTests(TestCase):
    """Tests for audit logging of mock endpoint access (serving responses)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.endpoint = MockEndpoint.objects.create(
            path="test/audit-access",
            owner=self.user,
            creator=self.user
        )
        self.handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"status": "ok"}'
        )

    # --- Successful Access ---
    def test_mock_endpoint_access_logged(self):
        """Accessing a mock endpoint creates an audit log entry."""
        initial_count = AuditLog.objects.count()
        self.client.get('/test/audit-access')
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_mock_access_log_includes_http_method(self):
        """Mock access audit log includes the HTTP method used."""
        self.client.get('/test/audit-access')
        log = AuditLog.objects.latest('timestamp')
        self.assertIn('GET', str(log.new_value))

    def test_mock_access_log_includes_endpoint_id(self):
        """Mock access audit log includes endpoint_id."""
        self.client.get('/test/audit-access')
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.endpoint_id, self.endpoint.id)

    # --- Auth Failures on Mock Endpoints ---
    def test_mock_auth_failure_logged(self):
        """Failed authentication on mock endpoint is logged."""
        auth_profile = AuthenticationProfile.objects.create(
            name='Auth Test',
            auth_type='api_key',
            api_key='correct-key',
            owner=self.user
        )
        self.endpoint.authentication = auth_profile
        self.endpoint.save()
        initial_count = AuditLog.objects.count()
        self.client.get('/test/audit-access', HTTP_X_API_KEY='wrong-key')
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_mock_auth_failure_log_has_correct_action(self):
        """Mock auth failure log has action='AUTH_FAILURE'."""
        auth_profile = AuthenticationProfile.objects.create(
            name='Auth Failure Test',
            auth_type='api_key',
            api_key='correct-key',
            owner=self.user
        )
        self.endpoint.authentication = auth_profile
        self.endpoint.save()
        self.client.get('/test/audit-access', HTTP_X_API_KEY='wrong-key')
        log = AuditLog.objects.filter(action='AUTH_FAILURE').latest('timestamp')
        self.assertEqual(log.action, 'AUTH_FAILURE')


class AuditLogAuthEventTests(TestCase):
    """Tests for audit logging of user authentication events."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')

    # --- Login ---
    def test_successful_login_logged(self):
        """Successful user login creates an audit log entry."""
        initial_count = AuditLog.objects.count()
        self.client.post(
            '/_mokkapi_api/login/',
            data={'username': 'testuser', 'password': 'testpass'}
        )
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_login_log_has_correct_action(self):
        """Login audit log has action='LOGIN'."""
        self.client.post(
            '/_mokkapi_api/login/',
            data={'username': 'testuser', 'password': 'testpass'}
        )
        log = AuditLog.objects.filter(action='LOGIN').latest('timestamp')
        self.assertEqual(log.action, 'LOGIN')

    def test_failed_login_logged(self):
        """Failed login attempt creates an audit log entry."""
        initial_count = AuditLog.objects.count()
        self.client.post(
            '/_mokkapi_api/login/',
            data={'username': 'testuser', 'password': 'wrongpass'}
        )
        self.assertGreater(AuditLog.objects.count(), initial_count)

    def test_failed_login_does_not_record_password(self):
        """Failed login log does NOT record attempted password."""
        self.client.post(
            '/_mokkapi_api/login/',
            data={'username': 'testuser', 'password': 'secretpassword'}
        )
        log = AuditLog.objects.latest('timestamp')
        self.assertNotIn('secretpassword', str(log.new_value))
        self.assertNotIn('secretpassword', str(log.old_value))

    # --- Logout ---
    def test_logout_logged(self):
        """User logout creates an audit log entry."""
        self.client.login(username='testuser', password='testpass')
        initial_count = AuditLog.objects.count()
        self.client.post('/_mokkapi_api/logout/')
        self.assertGreater(AuditLog.objects.count(), initial_count)


class AuditLogQueryTests(TestCase):
    """Tests for querying and filtering audit logs."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.admin = User.objects.create_superuser(username='admin', password='admin')
        self.api_base = '/_mokkapi_api/api'

    # --- Filtering ---
    def test_filter_by_user(self):
        """Can filter audit logs by user."""
        AuditLog.objects.create(user=self.user, action='CREATE', endpoint_id=1)
        AuditLog.objects.create(user=self.admin, action='CREATE', endpoint_id=2)
        user_logs = AuditLog.objects.filter(user=self.user)
        self.assertEqual(user_logs.count(), 1)

    def test_filter_by_action(self):
        """Can filter audit logs by action type."""
        AuditLog.objects.create(user=self.user, action='CREATE', endpoint_id=1)
        AuditLog.objects.create(user=self.user, action='DELETE', endpoint_id=1)
        create_logs = AuditLog.objects.filter(action='CREATE')
        self.assertEqual(create_logs.count(), 1)

    def test_filter_by_endpoint_id(self):
        """Can filter audit logs by endpoint_id."""
        AuditLog.objects.create(user=self.user, action='CREATE', endpoint_id=1)
        AuditLog.objects.create(user=self.user, action='CREATE', endpoint_id=2)
        endpoint_logs = AuditLog.objects.filter(endpoint_id=1)
        self.assertEqual(endpoint_logs.count(), 1)

    # --- Access Control ---
    def test_user_sees_only_own_audit_logs(self):
        """Regular user can only see their own audit logs."""
        AuditLog.objects.create(user=self.user, action='CREATE', endpoint_id=1)
        AuditLog.objects.create(user=self.admin, action='CREATE', endpoint_id=2)
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(f'{self.api_base}/audit-logs/')
        data = response.json()
        for log in data:
            self.assertEqual(log.get('user'), self.user.id)

    def test_admin_sees_all_audit_logs(self):
        """Admin can see all audit logs."""
        AuditLog.objects.create(user=self.user, action='CREATE', endpoint_id=1)
        AuditLog.objects.create(user=self.admin, action='CREATE', endpoint_id=2)
        self.client.login(username='admin', password='admin')
        response = self.client.get(f'{self.api_base}/audit-logs/')
        data = response.json()
        self.assertGreaterEqual(len(data), 2)

    def test_audit_logs_are_read_only(self):
        """Audit logs cannot be modified via API."""
        log = AuditLog.objects.create(user=self.user, action='CREATE', endpoint_id=1)
        self.client.login(username='admin', password='admin')
        response = self.client.patch(
            f'{self.api_base}/audit-logs/{log.id}/',
            data=json.dumps({'action': 'DELETE'}),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [403, 405])


class AuditLogIntegrityTests(TestCase):
    """Tests for audit log data integrity and reliability."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    # --- Immutability ---
    def test_audit_log_cannot_be_updated(self):
        """Audit log entries cannot be modified after creation."""
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            endpoint_id=1
        )
        log.action = 'DELETE'
        try:
            log.save()
            log.refresh_from_db()
            self.assertEqual(log.action, 'CREATE')
        except Exception:
            pass  # Expected if modification is blocked

    def test_audit_log_cannot_be_deleted(self):
        """Audit log entries cannot be deleted."""
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            endpoint_id=1
        )
        log_id = log.id
        try:
            log.delete()
            self.assertTrue(AuditLog.objects.filter(id=log_id).exists())
        except Exception:
            pass  # Expected if deletion is blocked

    # --- User Deletion ---
    def test_audit_log_preserved_after_user_deletion(self):
        """Audit logs are preserved when user is deleted."""
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            endpoint_id=1
        )
        log_id = log.id
        self.user.delete()
        self.assertTrue(AuditLog.objects.filter(id=log_id).exists())

    def test_audit_log_user_null_after_user_deletion(self):
        """Audit log user becomes null after user deletion (SET_NULL)."""
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            endpoint_id=1
        )
        log_id = log.id
        self.user.delete()
        log.refresh_from_db()
        self.assertIsNone(log.user)

    # --- Endpoint Deletion ---
    def test_audit_log_preserved_after_endpoint_deletion(self):
        """Audit logs are preserved when endpoint is deleted."""
        endpoint = MockEndpoint.objects.create(
            path='test/delete-integrity',
            owner=self.user,
            creator=self.user
        )
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            endpoint_id=endpoint.id
        )
        log_id = log.id
        endpoint.delete()
        self.assertTrue(AuditLog.objects.filter(id=log_id).exists())

    def test_audit_log_endpoint_id_preserved_after_deletion(self):
        """Audit log endpoint_id value is preserved after endpoint deletion."""
        endpoint = MockEndpoint.objects.create(
            path='test/preserve-id',
            owner=self.user,
            creator=self.user
        )
        endpoint_id = endpoint.id
        log = AuditLog.objects.create(
            user=self.user,
            action='DELETE',
            endpoint_id=endpoint_id
        )
        endpoint.delete()
        log.refresh_from_db()
        self.assertEqual(log.endpoint_id, endpoint_id)


class AuditLogAPIAccessTests(TestCase):
    """Tests for audit log API access control - admin only."""

    def setUp(self):
        self.client = Client()
        self.regular_user = User.objects.create_user(username='regular', password='pass123')
        self.admin_user = User.objects.create_superuser(username='admin', password='admin123')
        self.api_base = '/_mokkapi_api/api'

        # Create some audit logs for testing
        AuditLog.objects.create(
            user=self.regular_user,
            action='CREATE',
            endpoint_id=1
        )
        AuditLog.objects.create(
            user=self.admin_user,
            action='LOGIN',
            endpoint_id=None
        )

    # --- API Access Control ---
    def test_unauthenticated_user_cannot_access_api(self):
        """Unauthenticated users cannot access audit logs API."""
        response = self.client.get(f'{self.api_base}/audit-logs/')
        self.assertIn(response.status_code, [401, 403])

    def test_regular_user_cannot_access_api(self):
        """Regular (non-admin) users cannot access audit logs API."""
        self.client.login(username='regular', password='pass123')
        response = self.client.get(f'{self.api_base}/audit-logs/')
        self.assertEqual(response.status_code, 403)

    def test_admin_user_can_access_api(self):
        """Admin users can access audit logs API."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'{self.api_base}/audit-logs/')
        self.assertEqual(response.status_code, 200)

    def test_admin_can_list_all_audit_logs(self):
        """Admin can list all audit logs via API."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'{self.api_base}/audit-logs/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 2)

    def test_admin_can_retrieve_single_audit_log(self):
        """Admin can retrieve a single audit log via API."""
        log = AuditLog.objects.first()
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'{self.api_base}/audit-logs/{log.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], log.id)

    def test_regular_user_cannot_retrieve_single_audit_log(self):
        """Regular user cannot retrieve a single audit log via API."""
        log = AuditLog.objects.first()
        self.client.login(username='regular', password='pass123')
        response = self.client.get(f'{self.api_base}/audit-logs/{log.id}/')
        self.assertEqual(response.status_code, 403)

    # --- API is Read-Only ---
    def test_admin_cannot_create_audit_log_via_api(self):
        """Admin cannot create audit logs via API (read-only)."""
        self.client.login(username='admin', password='admin123')
        response = self.client.post(
            f'{self.api_base}/audit-logs/',
            data=json.dumps({'action': 'CREATE', 'endpoint_id': 1}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 405)

    def test_admin_cannot_update_audit_log_via_api(self):
        """Admin cannot update audit logs via API (read-only)."""
        log = AuditLog.objects.first()
        self.client.login(username='admin', password='admin123')
        response = self.client.patch(
            f'{self.api_base}/audit-logs/{log.id}/',
            data=json.dumps({'action': 'DELETE'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 405)

    def test_admin_cannot_delete_audit_log_via_api(self):
        """Admin cannot delete audit logs via API (read-only)."""
        log = AuditLog.objects.first()
        self.client.login(username='admin', password='admin123')
        response = self.client.delete(f'{self.api_base}/audit-logs/{log.id}/')
        self.assertEqual(response.status_code, 405)

    # --- API Filtering ---
    def test_api_filter_by_action(self):
        """Admin can filter audit logs by action type."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'{self.api_base}/audit-logs/?action=CREATE')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for log in data:
            self.assertEqual(log['action'], 'CREATE')

    def test_api_filter_by_user(self):
        """Admin can filter audit logs by user ID."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'{self.api_base}/audit-logs/?user={self.regular_user.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for log in data:
            self.assertEqual(log['user'], self.regular_user.id)


class AuditLogWebViewAccessTests(TestCase):
    """Tests for audit log web view access control - admin only."""

    def setUp(self):
        self.client = Client()
        self.regular_user = User.objects.create_user(username='regular', password='pass123')
        self.admin_user = User.objects.create_superuser(username='admin', password='admin123')
        self.audit_logs_url = '/_mokkapi_api/audit-logs/'

        # Create an audit log for testing
        AuditLog.objects.create(
            user=self.regular_user,
            action='CREATE',
            endpoint_id=1
        )

    # --- Web View Access Control ---
    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated users are redirected to login."""
        response = self.client.get(self.audit_logs_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_regular_user_gets_forbidden(self):
        """Regular (non-admin) users get 403 Forbidden."""
        self.client.login(username='regular', password='pass123')
        response = self.client.get(self.audit_logs_url)
        self.assertEqual(response.status_code, 403)

    def test_admin_user_can_access_web_view(self):
        """Admin users can access the audit logs web view."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(self.audit_logs_url)
        self.assertEqual(response.status_code, 200)

    def test_admin_web_view_displays_audit_logs(self):
        """Admin web view displays audit log entries."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(self.audit_logs_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CREATE')

    def test_admin_web_view_with_action_filter(self):
        """Admin can filter audit logs by action in web view."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'{self.audit_logs_url}?action=CREATE')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CREATE')

    def test_admin_web_view_with_user_filter(self):
        """Admin can filter audit logs by username in web view."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'{self.audit_logs_url}?user=regular')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'regular')
