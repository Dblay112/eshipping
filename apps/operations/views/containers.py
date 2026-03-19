from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ContainerListUploadForm
from ..models import ContainerListUpload, SDRecord
from ..permissions import can_manage_sd_records


# ══════════════════════════════════════════════════════
#  CONTAINER LIST UPLOADS
# ══════════════════════════════════════════════════════

@login_required(login_url='login')
def container_list_view(request, pk):
    """
    View and upload container lists (Excel) for a specific SD record.

    Features:
    - Display all uploaded container lists for an SD
    - Upload new Excel files per contract allocation
    - Auto-populates contract number from linked allocation
    - Shows uploader and upload timestamp
    - Supports multiple uploads per SD (one per contract)

    Security:
    - All authenticated users can view container lists
    - Only operations desk can upload new lists

    Permissions:
    - View: All authenticated users
    - Upload: OPERATIONS desk or superuser only

    Args:
        pk: Primary key of SDRecord to view/upload container lists for

    Returns:
        GET: Renders container list view with upload form
        POST: Uploads container list and redirects to view
    """
    sd = get_object_or_404(SDRecord, pk=pk)
    uploads = ContainerListUpload.objects.filter(sd_record=sd).select_related('allocation', 'uploaded_by')
    can_manage = can_manage_sd_records(request.user)

    if request.method == 'POST':
        if not can_manage:
            messages.error(request, 'Only the Operations desk can upload container lists.')
            return redirect('container_list_view', pk=pk)
        form = ContainerListUploadForm(request.POST, request.FILES, sd_record=sd)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.sd_record = sd
            upload.uploaded_by = request.user
            # Auto-populate contract_number from linked allocation
            if upload.allocation and not upload.contract_number:
                upload.contract_number = upload.allocation.contract_number
            upload.save()
            messages.success(request, 'Container list uploaded successfully.')
            return redirect('container_list_view', pk=pk)
        messages.error(request, 'Please fix the errors below.')
    else:
        form = ContainerListUploadForm(sd_record=sd)

    return render(request, 'sd/container_list.html', {
        'sd': sd,
        'uploads': uploads,
        'form': form,
        'can_manage': can_manage,
    })


@login_required(login_url='login')
def container_list_delete(request, pk, upload_pk):
    """
    Delete a container list upload (operations desk only).

    Features:
    - Deletes uploaded Excel file from storage
    - Removes database record
    - No confirmation page (direct deletion)

    Security:
    - Only operations desk can delete container lists
    - No ownership verification (any operations user can delete)

    Permissions: OPERATIONS desk or superuser only

    Args:
        pk: Primary key of SDRecord
        upload_pk: Primary key of ContainerListUpload to delete

    Returns:
        POST: Deletes upload and redirects to container list view
    """
    if not can_manage_sd_records(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('container_list_view', pk=pk)
    upload = get_object_or_404(ContainerListUpload, pk=upload_pk, sd_record__pk=pk)
    if request.method == 'POST':
        upload.excel_file.delete(save=False)
        upload.delete()
        messages.success(request, 'Container list removed.')
    return redirect('container_list_view', pk=pk)
