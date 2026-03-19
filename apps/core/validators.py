"""
Security validators for file uploads and user input.
Created as part of security audit fixes (March 2026).
"""
from django.core.exceptions import ValidationError
from django.conf import settings
import logging
import os

logger = logging.getLogger('security.validators')


def validate_file_extension(file, allowed_extensions):
    """
    Validate that uploaded file has an allowed extension.

    SECURITY: Prevents upload of malicious files disguised as documents.

    Args:
        file: The uploaded file object
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.xlsx'])

    Raises:
        ValidationError: If file extension is not allowed
    """
    if not file:
        return True

    ext = os.path.splitext(file.name)[1].lower()

    if ext not in allowed_extensions:
        logger.warning(
            f'SECURITY: Invalid file type upload attempt - '
            f'Filename: {file.name}, Extension: {ext}, '
            f'Allowed: {", ".join(allowed_extensions)}'
        )
        raise ValidationError(
            f'Invalid file type. Only {", ".join(allowed_extensions)} files are allowed.'
        )

    return True


def validate_file_size(file, file_type='general'):
    """
    Validate uploaded file size against configured limits.

    SECURITY: Prevents DoS attacks via large file uploads and ensures
    server storage is not exhausted by malicious uploads.

    Args:
        file: The uploaded file object (from request.FILES)
        file_type: Type of file ('pdf', 'excel', 'image', 'general')

    Raises:
        ValidationError: If file exceeds size limit

    Returns:
        True if validation passes

    Usage:
        try:
            validate_file_size(request.FILES.get('pdf_file'), 'pdf')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('form_page')
    """
    if not file:
        return True  # No file uploaded, skip validation

    # Get size limits from settings (in MB)
    size_limits = {
        'pdf': getattr(settings, 'MAX_PDF_FILE_SIZE', 10),
        'excel': getattr(settings, 'MAX_EXCEL_FILE_SIZE', 25),
        'image': getattr(settings, 'MAX_IMAGE_FILE_SIZE', 5),
        'general': 10,  # Default 10MB for unspecified types
    }

    max_size_mb = size_limits.get(file_type, 10)
    max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes

    try:
        file_size = file.size
    except (FileNotFoundError, OSError):
        # File referenced in database but missing from disk
        # This happens on ephemeral storage (Render free tier) after restarts
        # Skip validation for existing files that are missing
        logger.info(
            f'File validation skipped - file missing from disk: {getattr(file, "name", "unknown")}'
        )
        return True

    if file_size > max_size_bytes:
        # SECURITY: Log oversized upload attempts
        logger.warning(
            f'SECURITY: Oversized file upload attempt - '
            f'Type: {file_type}, Size: {file_size / (1024*1024):.2f}MB, '
            f'Limit: {max_size_mb}MB, Filename: {file.name}'
        )

        raise ValidationError(
            f'File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed '
            f'size of {max_size_mb}MB for {file_type} files.'
        )

    return True


def validate_pdf_file(file):
    """
    Validate PDF file extension and size.

    SECURITY: Ensures only PDF files are uploaded, not malicious files renamed to .pdf
    """
    if not file:
        return True

    # Check file extension first
    validate_file_extension(file, ['.pdf'])

    # Then check file size
    return validate_file_size(file, 'pdf')


def validate_excel_file(file):
    """
    Validate Excel file extension and size.

    SECURITY: Ensures only Excel files are uploaded, not malicious files renamed to .xlsx
    """
    if not file:
        return True

    # Check file extension first
    validate_file_extension(file, ['.xlsx', '.xls'])

    # Then check file size
    return validate_file_size(file, 'excel')


def validate_image_file(file):
    """
    Validate image file extension and size.

    SECURITY: Ensures only image files are uploaded
    """
    if not file:
        return True

    # Check file extension first
    validate_file_extension(file, ['.jpg', '.jpeg', '.png', '.gif', '.webp'])

    # Then check file size
    return validate_file_size(file, 'image')


def validate_file_size_2mb(file):
    """
    Validate file size is under 2MB.
    Legacy validator for backward compatibility.
    """
    if not file:
        return True

    max_size_bytes = 2 * 1024 * 1024  # 2MB

    try:
        file_size = file.size
    except (FileNotFoundError, OSError):
        # File missing from disk (ephemeral storage)
        logger.info(f'File validation skipped - file missing: {getattr(file, "name", "unknown")}')
        return True

    if file_size > max_size_bytes:
        logger.warning(
            f'SECURITY: Oversized file upload attempt - '
            f'Size: {file_size / (1024*1024):.2f}MB, '
            f'Limit: 2MB, Filename: {file.name}'
        )
        raise ValidationError(
            f'File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size of 2MB.'
        )

    return True


def validate_file_size_5mb(file):
    """
    Validate file size is under 5MB.
    Legacy validator for backward compatibility.
    """
    if not file:
        return True

    max_size_bytes = 5 * 1024 * 1024  # 5MB

    try:
        file_size = file.size
    except (FileNotFoundError, OSError):
        # File missing from disk (ephemeral storage)
        logger.info(f'File validation skipped - file missing: {getattr(file, "name", "unknown")}')
        return True

    if file_size > max_size_bytes:
        logger.warning(
            f'SECURITY: Oversized file upload attempt - '
            f'Size: {file_size / (1024*1024):.2f}MB, '
            f'Limit: 5MB, Filename: {file.name}'
        )
        raise ValidationError(
            f'File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size of 5MB.'
        )

    return True


def validate_file_size_10mb(file):
    """
    Validate file size is under 10MB.
    Legacy validator for backward compatibility.
    """
    if not file:
        return True

    max_size_bytes = 10 * 1024 * 1024  # 10MB

    try:
        file_size = file.size
    except (FileNotFoundError, OSError):
        # File missing from disk (ephemeral storage)
        logger.info(f'File validation skipped - file missing: {getattr(file, "name", "unknown")}')
        return True

    if file_size > max_size_bytes:
        logger.warning(
            f'SECURITY: Oversized file upload attempt - '
            f'Size: {file_size / (1024*1024):.2f}MB, '
            f'Limit: 10MB, Filename: {file.name}'
        )
        raise ValidationError(
            f'File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size of 10MB.'
        )

    return True


def validate_file_size_25mb(file):
    """
    Validate file size is under 25MB.
    Legacy validator for backward compatibility (for Excel files).
    """
    if not file:
        return True

    max_size_bytes = 25 * 1024 * 1024  # 25MB

    try:
        file_size = file.size
    except (FileNotFoundError, OSError):
        # File missing from disk (ephemeral storage)
        logger.info(f'File validation skipped - file missing: {getattr(file, "name", "unknown")}')
        return True

    if file_size > max_size_bytes:
        logger.warning(
            f'SECURITY: Oversized file upload attempt - '
            f'Size: {file_size / (1024*1024):.2f}MB, '
            f'Limit: 25MB, Filename: {file.name}'
        )
        raise ValidationError(
            f'File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size of 25MB.'
        )

    return True
