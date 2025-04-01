from django.urls import path
from django.contrib.auth import views as auth_views
from .views import account_view, export_endpoints_view, home_view, serve_json_view

urlpatterns = [
    path('', home_view, name='home'),
    path('account', account_view, name='account'),
    path('login', auth_views.LoginView.as_view(template_name='mokkapi/login.html'), name='login'),
    path('logout', auth_views.LogoutView.as_view(), name='logout'),
    path('export', export_endpoints_view, name='export'),
    path('<path:endpoint_path>', serve_json_view, name='serve_json'),
#    path('<path:url_path>', get_json_content, name='get_json_content'),
]
