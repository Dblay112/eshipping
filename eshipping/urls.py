import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from apps.core.views import serve_protected_media

# Security: Use custom admin URL from environment variable
# Default to 'admin/' for development, but change in production
ADMIN_URL = os.getenv('ADMIN_URL', 'admin/')

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='login', permanent=False)),
    path('', include('apps.accounts.urls')),
    path('', include('apps.tally.urls')),
    path('', include('apps.operations.urls')),
    path('', include('apps.ebooking.urls')),
    path('', include('apps.declaration.urls')),
    path('', include('apps.evacuation.urls')),
    path(ADMIN_URL, admin.site.urls),
    # SECURITY: Diagnostic endpoints removed - they exposed database structure without authentication
    # If needed for troubleshooting, use Django management commands instead:
    # - python manage.py showmigrations
    # - python manage.py migrate
    # - python manage.py createsuperuser
    # Protected media file serving (requires authentication)
    re_path(r'^media/(?P<file_path>.*)$', serve_protected_media, name='serve_protected_media'),
]

# Only serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
