"""
Protected file serving for media files.
Ensures only authenticated users with proper permissions can access uploaded files.
"""
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.conf import settings
from io import StringIO
import os
import logging

logger = logging.getLogger(__name__)


@login_required(login_url='login')
def serve_protected_media(request, file_path):
    """
    Serve media files with authentication and access control.

    Provides secure file serving for uploaded documents (PDFs, Excel files, images).
    Only authenticated users can access files. Prevents directory traversal attacks.

    Features:
    - Authentication required (login_required decorator)
    - Directory traversal protection
    - Audit logging for file access
    - Mobile-friendly (forces download on mobile browsers)
    - Proper content-type headers for different file types

    Security:
    - Validates file path to prevent directory traversal
    - Logs all file access attempts for audit trail
    - Returns 404 if file doesn't exist
    - Returns 403 if path is invalid

    Mobile Fix:
    - Uses 'attachment' disposition to force download
    - Ensures files download properly on iOS Safari and mobile browsers
    - Prevents inline display issues on mobile devices

    Args:
        request: Django HttpRequest object
        file_path: Relative path to file within MEDIA_ROOT

    Returns:
        FileResponse: File download response with proper headers

    Raises:
        PermissionDenied: If directory traversal detected
        Http404: If file doesn't exist

    Example:
        URL pattern: /media/declaration_docs/file.pdf
        Serves: MEDIA_ROOT/declaration_docs/file.pdf

    TODO:
        Add additional permission checks based on:
        - File ownership (check if user created the record)
        - Desk membership (check if user belongs to relevant desk)
        - Manager status (allow managers to access all files)
    """
    # Construct full file path
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)

    # Security check: prevent directory traversal attacks
    if not os.path.abspath(full_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        logger.warning(f'Directory traversal attempt by user {request.user.pk}: {file_path}')
        raise PermissionDenied("Invalid file path")

    # Check if file exists
    if not os.path.exists(full_path):
        logger.info(f'File not found: {file_path}')
        raise Http404("File not found")

    # TODO: Add additional permission checks here based on your requirements
    # Example: Check if user has permission to access this specific file
    # if not user_has_permission_for_file(request.user, file_path):
    #     raise PermissionDenied("You don't have permission to access this file")

    # Log file access for audit trail
    logger.info(f'User {request.user.pk} accessed file: {file_path}')

    # Serve the file
    response = FileResponse(open(full_path, 'rb'))

    # MOBILE FIX: Always use 'attachment' to force download on mobile browsers
    # This ensures files download properly on iOS Safari and other mobile browsers
    # instead of trying to open inline which often fails
    filename = os.path.basename(full_path)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Set proper content type
    file_ext = os.path.splitext(full_path)[1].lower()
    content_types = {
        '.pdf': 'application/pdf',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.csv': 'text/csv',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
    }
    if file_ext in content_types:
        response['Content-Type'] = content_types[file_ext]

    return response


@login_required(login_url='login')
def run_migrations_endpoint(request):
    """
    Emergency endpoint to run database migrations manually via HTTP request.

    SECURITY WARNING: This endpoint is disabled by default (not routed in urls.py).
    Only enable temporarily for emergency troubleshooting on production servers
    where direct shell access is unavailable.

    Recommended Approach:
    - Use Django management commands instead: python manage.py migrate
    - Only enable this endpoint as a last resort

    Features:
    - Runs Django migrations programmatically
    - Captures stdout and stderr output
    - Returns JSON response with migration results
    - Requires POST request (prevents accidental GET triggers)

    Security:
    - Requires authentication (login_required decorator)
    - Requires superuser privileges (is_superuser check)
    - Logs unauthorized access attempts
    - POST-only to prevent CSRF and accidental triggers

    Permissions:
    - Superuser only (is_superuser=True)

    Args:
        request: Django HttpRequest object

    Returns:
        JsonResponse: Migration results with status, stdout, stderr
        HttpResponse: 405 error if not POST request

    Raises:
        PermissionDenied: If user is not superuser

    Example Response (Success):
        {
            "status": "success",
            "message": "Migrations completed successfully",
            "stdout": "Operations to perform:\n  Apply all migrations...",
            "stderr": ""
        }

    Example Response (Error):
        {
            "status": "error",
            "error": "Migration failed: ...",
            "stdout": "...",
            "stderr": "..."
        }

    Usage:
        1. Temporarily add route to urls.py:
           path('admin/run-migrations/', views.run_migrations_endpoint)
        2. Send POST request to /admin/run-migrations/
        3. Remove route after emergency is resolved
    """
    # SECURITY: Only superusers can run migrations
    if not request.user.is_superuser:
        logger.warning(f'Unauthorized migration attempt by user {request.user.pk}')
        raise PermissionDenied("Only superusers can run migrations")

    if request.method != 'POST':
        return HttpResponse("POST request required. Send POST to this URL to run migrations.", status=405)

    try:
        out = StringIO()
        err = StringIO()
        call_command('migrate', '--verbosity', '2', stdout=out, stderr=err)
        return JsonResponse({
            'status': 'success',
            'message': 'Migrations completed successfully',
            'stdout': out.getvalue(),
            'stderr': err.getvalue(),
        }, json_dumps_params={'indent': 2})
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'stdout': out.getvalue() if 'out' in locals() else '',
            'stderr': err.getvalue() if 'err' in locals() else '',
        }, status=500, json_dumps_params={'indent': 2})
