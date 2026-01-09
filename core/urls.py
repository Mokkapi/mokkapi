from django.contrib.auth import views as auth_views
from django.urls import include, path

from rest_framework.authtoken import views as authtoken_views
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r'auth-profiles', views.AuthenticationProfileViewSet, basename='authprofile')
router.register(r'endpoints', views.MockEndpointViewSet, basename='mockendpoint')
router.register(r'handlers', views.ResponseHandlerViewSet, basename='handler')
router.register(r'audit-logs', views.AuditLogViewSet, basename='auditlog')



urlpatterns = [
    path('', views.home_view, name='home'),
    path('admin/', views.admin_view, name='admin'),
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
    path('api/', include(router.urls)),
    path('app/', views.react_app, name='react_app'),
    path('whoami/', views.whoami, name='whoami-api'),
    #path('api-token-auth/', authtoken_views.obtain_auth_token, name='api_token_auth'),
    path('license/', include('license.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='mokkapi/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
