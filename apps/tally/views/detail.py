"""Tally detail / PDF / delete views.

Mechanically extracted from views_old.py to keep behavior unchanged.
"""

import datetime
import io
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.operations.models import SDRecord, get_current_crop_year_choices
from apps.tally.utils import _safe_str, _safe_date

from ..models import TallyInfo, Terminal, TallyContainer

from ._old_shared import _can_view_tally, _parse_container_indices
from .exports import export_tally_excel

import logging

logger = logging.getLogger(__name__)


def _paginate_containers(tally):
    """
    Paginate tally containers based on tally type.

    Different tally types have different containers-per-page limits:
    - JAPAN_STRAIGHT_40FT: 6 containers per page
    - BULK: 16 containers per page
    - STRAIGHT_20FT/STRAIGHT_40FT: 8 containers per page

    Args:
        tally: TallyInfo instance with containers relationship

    Returns:
        List of dicts with 'containers' key containing container lists
    """
    containers = list(tally.containers.all().order_by("id"))
    pages = []

    if tally.tally_type == "JAPAN_STRAIGHT_40FT":
        # All containers fit on one sheet if <= 6; if more, first page gets
        # as many as needed, color tags follow on the same page, overflow continues.
        # Per the spec: max 6 per sheet for Japan.
        for i in range(0, len(containers), 6):
            pages.append({"containers": containers[i:i + 6]})
    elif tally.tally_type == "BULK":
        # BULK: 16 containers per page
        for i in range(0, len(containers), 16):
            pages.append({"containers": containers[i:i + 16]})
    else:
        # STRAIGHT_20FT, STRAIGHT_40FT: 8 containers per page
        for i in range(0, len(containers), 8):
            pages.append({"containers": containers[i:i + 8]})

    if not pages:
        pages = [{"containers": []}]

    return pages


@login_required(login_url='login')
def tally_excel(request, pk):
    """
    Export tally to Excel format.

    Delegates to export_tally_excel function for actual export logic.

    Args:
        pk: Primary key of TallyInfo to export

    Returns:
        Excel file download response
    """
    return export_tally_excel(request, pk)


@login_required(login_url='login')
def tally_view(request, pk):
    """
    Display tally details in digital format.

    Features:
    - Shows all tally information and containers
    - Paginated container display based on tally type
    - Shows recall request history
    - Hides navbar for clean printing

    Permissions: Creator, terminal supervisors, managers, or superuser

    Args:
        pk: Primary key of TallyInfo to view

    Returns:
        Renders tally_digital.html with tally details
    """
    tally = get_object_or_404(
        TallyInfo.objects.prefetch_related("containers"),
        pk=pk,
    )
    if not _can_view_tally(request.user, tally):
        messages.error(
            request, "You don't have permission to view this tally.")
        return redirect("my_tallies")

    # Fetch recall request history for this tally
    from apps.tally.models import RecallRequest
    recall_requests = RecallRequest.objects.filter(
        tally=tally
    ).select_related('requested_by', 'approved_by').order_by('-created_at')

    # Use extracted pagination function
    pages = _paginate_containers(tally)

    return render(
        request,
        "tally_details/tally_digital.html",
        {
            "tally": tally,
            "pages": pages,
            "recall_requests": recall_requests,
            "hide_nav": True,   # ✅ this hides navbar + removes padding
        },
    )


@login_required(login_url='login')
def tally_pdf(request, pk):
    """
    Export tally to PDF format with professional formatting.

    Features:
    - Generates PDF using ReportLab with A4 page size
    - Professional header with company name and department
    - Displays all tally information (crop year, SD, MK, vessel, etc.)
    - Table layout with container details (number, seal, bags, tonnage)
    - Paginated output (8 containers per page)
    - Grand totals for bags and tonnage
    - For bulk tallies: includes bags saved/lost calculation
    - Signature boxes for superintendent and clerks
    - Page numbers (Page X of Y)

    Layout:
    - BULK: 4 columns (Container Number, Tonnage, Seal Number, Total Bags)
    - STRAIGHT: 3 columns (Container Number, Seal Number, Total Bags)

    Security:
    - Permission check: only creator, supervisors, or managers can download
    - Uses _can_view_tally helper for authorization

    Permissions: Creator, terminal supervisors, managers, or superuser

    Args:
        pk: Primary key of TallyInfo to export

    Returns:
        PDF file download with formatted tally data
        Or redirects to my_tallies if permission denied
    """
    tally = get_object_or_404(
        TallyInfo.objects.prefetch_related("containers"),
        pk=pk,
    )
    if not _can_view_tally(request.user, tally):
        messages.error(
            request, "You don't have permission to download this tally.")
        return redirect("my_tallies")
    containers = list(tally.containers.all().order_by("id"))

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    per_page = 8

    def _bags_for(cc):
        if tally.tally_type == "BULK":
            return cc.bags_cut if cc.bags_cut is not None else (cc.bags or 0)
        return cc.bags if cc.bags is not None else 0

    def _ton_for(cc):
        if cc.tonnage is not None:
            try:
                return float(cc.tonnage)
            except Exception:
                return 0.0
        try:
            return float(_bags_for(cc)) / 16.0
        except Exception:
            return 0.0

    sup_names = tally.superintendent_name if isinstance(
        tally.superintendent_name, list) else []
    clerk_names = tally.clerk_name if isinstance(
        tally.clerk_name, list) else []

    def draw_page(page_containers, page_no, total_pages):
        margin = 12 * mm
        x0 = margin
        y0 = margin
        w = width - 2 * margin
        h = height - 2 * margin

        c.setStrokeColor(colors.black)
        c.setLineWidth(2)
        c.rect(x0, y0, w, h)

        top = height - margin

        c.setFont("Times-Bold", 12)
        c.drawCentredString(width / 2, top - 10 * mm,
                            "COCOA MARKETING COMPANY (GHANA) LTD.")
        c.setFont("Times-Bold", 10)
        c.drawCentredString(width / 2, top - 16 * mm,
                            "(SHIPPING DEPARTMENT)")

        c.setFont("Times-Bold", 9)
        c.drawString(x0 + 5 * mm, top - 24 * mm,
                     f"CROP YEAR: {_safe_str(tally.crop_year)}")
        c.drawRightString(width - margin - 5 * mm, top - 24 * mm,
                          f"T N° {_safe_str(tally.tally_number)}")

        c.setFont("Times-Roman", 9)
        c.drawString(x0 + 5 * mm, top - 30 * mm,
                     f"SD NUMBER: {_safe_str(tally.sd_number)}")
        c.drawString(x0 + 5 * mm, top - 36 * mm,
                     f"MK NUMBER: {_safe_str(tally.mk_number)}")

        c.drawRightString(width - margin - 5 * mm, top - 30 * mm,
                          f"COCOA TYPE: {_safe_str(tally.cocoa_type or 'GRADE I')}")
        c.drawRightString(width - margin - 5 * mm, top - 36 * mm,
                          f"DRY BAGS: {_safe_str(tally.dry_bags or 'NIL')}")

        c.setFont("Times-Bold", 10)
        c.drawCentredString(width / 2, top - 44 * mm, "EXPORT TALLIES")

        c.setFont("Times-Roman", 9)
        c.drawString(x0 + 5 * mm, top - 52 * mm,
                     f"S.S/M.S: {_safe_str(tally.vessel)}")
        c.drawString(x0 + 5 * mm, top - 58 * mm,
                     f"TERMINAL: {_safe_str(tally.terminal_name)}")

        c.drawString(x0 + (w / 2), top - 52 * mm,
                     f"DESTINATION: {_safe_str(tally.destination)}")
        c.drawString(x0 + (w / 2), top - 58 * mm,
                     f"DATE: {_safe_date(tally.loading_date)}")

        c.setLineWidth(1)

        table_top = top - 74 * mm
        row_h = 10 * mm

        left_pad = 5 * mm
        right_pad = 5 * mm
        colL = x0 + left_pad
        colR = x0 + w - right_pad

        is_bulk = (tally.tally_type == "BULK")

        if is_bulk:
            col2 = x0 + (w * 0.45)
            col3 = x0 + (w * 0.60)
            col4 = x0 + (w * 0.82)

            c.setFillColor(colors.black)
            c.rect(x0, table_top, w, row_h, fill=1, stroke=1)
            c.setFillColor(colors.white)
            c.setFont("Times-Bold", 9)
            c.drawCentredString((colL + col2) / 2,
                                table_top + 3 * mm, "CONTAINER NUMBER")
            c.drawCentredString((col2 + col3) / 2,
                                table_top + 3 * mm, "TONNAGE")
            c.drawCentredString((col3 + col4) / 2,
                                table_top + 3 * mm, "SEAL NUMBER")
            c.drawCentredString((col4 + colR) / 2,
                                table_top + 3 * mm, "TOTAL BAGS")

            c.setFillColor(colors.black)
            y = table_top - row_h
            c.setFont("Times-Roman", 9)

            for i in range(per_page):
                c.rect(x0, y, w, row_h, fill=0, stroke=1)
                c.line(col2, y, col2, y + row_h)
                c.line(col3, y, col3, y + row_h)
                c.line(col4, y, col4, y + row_h)

                if i < len(page_containers):
                    cc = page_containers[i]
                    bags_val = _bags_for(cc)
                    ton_val = _ton_for(cc)

                    c.drawString(colL + 2 * mm, y + 3 * mm,
                                 _safe_str(cc.container_number))
                    c.drawRightString(col3 - 2 * mm, y + 3 * mm,
                                      f"{ton_val:.3f}")
                    c.drawString(col3 + 2 * mm, y + 3 * mm,
                                 _safe_str(cc.seal_number))
                    c.drawRightString(colR - 2 * mm, y + 3 * mm,
                                      _safe_str(bags_val))

                y -= row_h
        else:
            col2 = x0 + (w * 0.62)
            col3 = x0 + (w * 0.82)

            c.setFillColor(colors.black)
            c.rect(x0, table_top, w, row_h, fill=1, stroke=1)
            c.setFillColor(colors.white)
            c.setFont("Times-Bold", 9)
            c.drawCentredString((colL + col2) / 2,
                                table_top + 3 * mm, "CONTAINER NUMBER")
            c.drawCentredString((col2 + col3) / 2,
                                table_top + 3 * mm, "SEAL NUMBER")
            c.drawCentredString((col3 + colR) / 2,
                                table_top + 3 * mm, "TOTAL BAGS")

            c.setFillColor(colors.black)
            y = table_top - row_h
            c.setFont("Times-Roman", 9)

            for i in range(per_page):
                c.rect(x0, y, w, row_h, fill=0, stroke=1)
                c.line(col2, y, col2, y + row_h)
                c.line(col3, y, col3, y + row_h)

                if i < len(page_containers):
                    cc = page_containers[i]
                    bags_val = _bags_for(cc)

                    c.drawString(colL + 2 * mm, y + 3 * mm,
                                 _safe_str(cc.container_number))
                    c.drawString(col2 + 2 * mm, y + 3 * mm,
                                 _safe_str(cc.seal_number))
                    c.drawRightString(colR - 2 * mm, y + 3 * mm,
                                      _safe_str(bags_val))

                y -= row_h

        c.setFont("Times-Bold", 9)
        c.drawRightString(colR, y + 10 * mm,
                          f"GRAND TOTAL BAGS: {_safe_str(tally.total_bags)}")
        c.drawRightString(
            colR, y + 5 * mm,
            f"GRAND TOTAL TONNAGE: {float(tally.total_tonnage or 0):.3f} MT"
        )

        if is_bulk:
            c.drawRightString(
                colR, y,
                f"BAGS SAVED/LOST: {_safe_str(tally.bags_saved)}"
            )

        sig_y_top = y0 + 38 * mm
        box_h = 20 * mm
        box_w = (w - 10 * mm) / 2
        gap = 10 * mm

        sup_x = x0 + 5 * mm
        clk_x = sup_x + box_w + gap

        c.setLineWidth(1)
        c.rect(sup_x, sig_y_top, box_w, box_h)
        c.rect(clk_x, sig_y_top, box_w, box_h)

        c.setFont("Times-Bold", 8)
        c.drawString(sup_x + 2 * mm, sig_y_top +
                     box_h - 6 * mm, "SUPERINTENDENT:")
        c.drawString(clk_x + 2 * mm, sig_y_top +
                     box_h - 6 * mm, "CLERK(S):")

        c.setFont("Times-Roman", 8)
        sup_text = "\n".join([str(x)
                             for x in sup_names if str(x).strip()])
        clk_text = "\n".join([str(x)
                             for x in clerk_names if str(x).strip()])

        t1 = c.beginText(sup_x + 2 * mm, sig_y_top + box_h - 10 * mm)
        for line in sup_text.split("\n"):
            t1.textLine(line[:60])
        c.drawText(t1)

        t2 = c.beginText(clk_x + 2 * mm, sig_y_top + box_h - 10 * mm)
        for line in clk_text.split("\n"):
            t2.textLine(line[:60])
        c.drawText(t2)

        c.setFont("Times-Roman", 8)
        c.drawCentredString(width / 2, y0 + 6 * mm,
                            f"PAGE {page_no} OF {total_pages}")

    total_pages = max(1, (len(containers) + per_page - 1) // per_page)

    for p in range(total_pages):
        start = p * per_page
        end = start + per_page
        draw_page(containers[start:end], p + 1, total_pages)
        if p < total_pages - 1:
            c.showPage()

    c.save()
    pdf = buf.getvalue()
    buf.close()

    filename = f"TALLY_{tally.tally_number}_{tally.tally_type}.pdf"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@login_required(login_url="login")
def tally_edit(request, pk):
    """
    Edit existing tally with full validation and container management.

    Features:
    - Edit all tally fields (crop year, SD, MK, vessel, terminal, etc.)
    - Add/remove/edit containers with validation
    - Preserves tally number and creator (immutable)
    - Updates existing containers or creates new ones
    - Deletes containers removed from form
    - Recalculates totals from container entries
    - Validates totals match sum of containers
    - Supports all tally types (BULK, STRAIGHT_20FT, STRAIGHT_40FT, JAPAN_STRAIGHT_40FT)
    - Audit trail with updated_by tracking

    Validation:
    - All required fields must be filled
    - At least one clerk name required
    - At least one container required
    - Superintendent name required if type != NONE
    - Total bags must equal sum of container bags
    - Total tonnage must equal sum of container tonnage
    - Bag counts and tonnage cannot be negative

    Security:
    - Permission check: only creator, supervisors, or managers can edit
    - Uses _can_view_tally helper for authorization
    - Transaction-based updates (all-or-nothing)

    Permissions: Creator, terminal supervisors, managers, or superuser

    Args:
        pk: Primary key of TallyInfo to edit

    Returns:
        GET: Renders tally form with existing data pre-filled
        POST: Updates tally and redirects to my_tallies
    """
    tally = get_object_or_404(
        TallyInfo.objects.prefetch_related("containers"),
        pk=pk,
    )
    if not _can_view_tally(request.user, tally):
        messages.error(
            request, "You don't have permission to edit this tally.")
        return redirect("my_tallies")

    template_map = {
        "BULK": "bulk/bulk_loading.html",
        "STRAIGHT_20FT": "straight_loading/20_straight_loading.html",
        "STRAIGHT_40FT": "straight_loading/40_straight_loading.html",
        "JAPAN_STRAIGHT_40FT": "straight_loading/japan_straight_loading.html",
    }

    template_name = template_map.get(tally.tally_type)
    if not template_name:
        messages.error(request, "Unsupported tally type for editing.")
        return redirect("my_tallies")

    # Prepare context for all renders
    terminals = Terminal.objects.all()
    crop_year_choices = get_current_crop_year_choices()
    all_sd_numbers = SDRecord.objects.values_list(
        'sd_number', flat=True).distinct()

    if request.method == "GET":
        containers = list(tally.containers.all().order_by("id"))

        # Build a JSON-friendly list the template/JS can use to prefill rows
        containers_payload = []
        for c in containers:
            containers_payload.append(
                {
                    "id": c.id,
                    "container_number": c.container_number,
                    "seal_number": c.seal_number,
                    "bags": c.bags,
                    "bags_cut": c.bags_cut,
                    "tonnage": str(c.tonnage) if c.tonnage is not None else "",
                }
            )

        context = {
            "edit_mode": True,
            "tally": tally,
            "containers_payload": containers_payload,
            "containers_payload_json": json.dumps(containers_payload),
            "terminals": terminals,
            "crop_year_choices": crop_year_choices,
            "all_sd_numbers": all_sd_numbers,
        }
        return render(request, template_name, context)

    # -----------------------
    # POST (SAVE EDITS)
    # -----------------------
    crop_year = request.POST.get("crop_year", "").strip()
    sd_number = request.POST.get("sd_number", "").strip()
    mk_number = request.POST.get("mk_number", "").strip()
    agent = request.POST.get("agent", "").strip()
    vessel = request.POST.get("vessel", "").strip()
    destination = request.POST.get("destination", "").strip()
    terminal_id = request.POST.get("terminal", "").strip()
    loading_date_raw = request.POST.get("loading_date", "").strip()
    marks_and_numbers = request.POST.get("marks_and_numbers", "").strip()
    cocoa_type = request.POST.get("cocoa_type", "").strip()
    superintendent_type = request.POST.get(
        "superintendent_type", "NONE").strip()

    # Straight-only
    dry_bags = (request.POST.get("dry_bags", "") or "").strip() or None

    required_fields = {
        "crop_year": crop_year,
        "sd_number": sd_number,
        "mk_number": mk_number,
        "vessel": vessel,
        "destination": destination,
        "terminal": terminal_id,
        "loading_date": loading_date_raw,
    }
    missing = [k for k, v in required_fields.items() if not v]
    if missing:
        messages.error(request, f"Missing required info: {', '.join(missing)}")
        return render(request, template_name, {
            "edit_mode": True,
            "tally": tally,
            "terminals": terminals,
            "crop_year_choices": crop_year_choices,
            "all_sd_numbers": all_sd_numbers,
        })

    try:
        loading_date = datetime.datetime.strptime(
            loading_date_raw, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        return render(request, template_name, {
            "edit_mode": True,
            "tally": tally,
            "terminals": terminals,
            "crop_year_choices": crop_year_choices,
            "all_sd_numbers": all_sd_numbers,
        })

    try:
        terminal_obj = Terminal.objects.get(id=terminal_id)
    except (Terminal.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Invalid terminal selected.")
        return render(request, template_name, {
            "edit_mode": True,
            "tally": tally,
            "terminals": terminals,
            "crop_year_choices": crop_year_choices,
            "all_sd_numbers": all_sd_numbers,
        })

    superintendent_names = [v.strip()
                            for v in request.POST.getlist("s_name") if v.strip()]
    clerk_names = [v.strip()
                   for v in request.POST.getlist("clerk_name") if v.strip()]

    if not clerk_names:
        messages.error(request, "At least one clerk name is required.")
        return render(request, template_name, {
            "edit_mode": True,
            "tally": tally,
            "terminals": terminals,
            "crop_year_choices": crop_year_choices,
            "all_sd_numbers": all_sd_numbers,
        })

    if superintendent_type != "NONE" and not superintendent_names:
        messages.error(request, "Superintendent name is required.")
        return render(request, template_name, {
            "edit_mode": True,
            "tally": tally,
            "terminals": terminals,
            "crop_year_choices": crop_year_choices,
            "all_sd_numbers": all_sd_numbers,
        })

    # BULK-only
    expected_bags = None
    actual_bags = None
    bags_saved = None

    if tally.tally_type == "BULK":
        try:
            expected_bags = int(request.POST.get("expected_bags", 0))
            actual_bags = int(request.POST.get("actual_bags", 0))
            if expected_bags < 0 or actual_bags < 0:
                raise ValueError("Bag counts cannot be negative")
            bags_saved = expected_bags - actual_bags
        except (ValueError, TypeError) as err:
            messages.error(request, f"Invalid bag count: {str(err)}")
            return render(request, template_name, {
                "edit_mode": True,
                "tally": tally,
                "terminals": terminals,
                "crop_year_choices": crop_year_choices,
                "all_sd_numbers": all_sd_numbers,
            })

    # Japan-only
    seller_codes = []
    color_tag_entries = []
    if tally.tally_type == "JAPAN_STRAIGHT_40FT":
        seller_codes = [v.strip() for v in request.POST.getlist(
            "seller_codes") if v.strip()]
        color_tag_entries = [v.strip() for v in request.POST.getlist(
            "color_tag_entries") if v.strip()]

    # Totals from form (still validate against calculated)
    total_bags_form_raw = (request.POST.get("total_bags", "0") or "0").strip()
    total_tonnage_form_raw = (request.POST.get(
        "total_tonnage", "0") or "0").strip()

    try:
        total_bags_form = int(Decimal(total_bags_form_raw or "0"))
    except (InvalidOperation, ValueError):
        total_bags_form = 0

    try:
        total_tonnage_form = Decimal(
            total_tonnage_form_raw or "0").quantize(Decimal("0.001"))
    except (InvalidOperation, ValueError):
        total_tonnage_form = Decimal("0.000")

    indices = _parse_container_indices(request)
    if not indices:
        messages.error(request, "At least one container is required.")
        return render(request, template_name, {
            "edit_mode": True,
            "tally": tally,
            "terminals": terminals,
            "crop_year_choices": crop_year_choices,
            "all_sd_numbers": all_sd_numbers,
        })

    existing = list(tally.containers.all())
    existing_by_id = {str(c.id): c for c in existing}
    used_ids = set()

    calculated_bags = 0
    calculated_tonnage = Decimal("0.000")
    max_size = 5 * 1024 * 1024

    # We'll create/update containers in a transaction, and delete removed ones.
    with transaction.atomic():
        # Update TallyInfo (DO NOT touch tally_number / created_by)
        tally.crop_year = crop_year
        tally.sd_number = sd_number
        tally.mk_number = mk_number
        tally.agent = agent
        tally.vessel = vessel
        tally.destination = destination
        tally.terminal_name = terminal_obj.name
        tally.terminal = terminal_obj
        tally.loading_date = loading_date
        tally.marks_and_numbers = marks_and_numbers or "GCB"
        tally.cocoa_type = cocoa_type
        tally.superintendent_type = superintendent_type
        tally.superintendent_name = superintendent_names
        tally.clerk_name = clerk_names

        if tally.tally_type == "BULK":
            tally.expected_bags = expected_bags
            tally.actual_bags = actual_bags
            tally.bags_saved = bags_saved

        if tally.tally_type in ("STRAIGHT_20FT", "STRAIGHT_40FT", "JAPAN_STRAIGHT_40FT"):
            tally.dry_bags = dry_bags

        if tally.tally_type == "JAPAN_STRAIGHT_40FT":
            tally.seller_codes = seller_codes
            tally.color_tag_entries = color_tag_entries

        # Containers
        for i in indices:
            cid = (request.POST.get(f"containers[{i}][id]") or "").strip()

            container_number = (request.POST.get(
                f"containers[{i}][container_number]") or "").strip()
            seal_number = (request.POST.get(
                f"containers[{i}][seal_number]") or "").strip()

            if not container_number:
                continue

            if not seal_number:
                messages.error(
                    request, f"Container {container_number}: Seal number is required.")
                raise transaction.TransactionManagementError(
                    "Validation error")

            # BULK vs STRAIGHT fields
            if tally.tally_type == "BULK":
                tonnage_str = (request.POST.get(
                    f"containers[{i}][tonnage]") or "").strip()
                bags_cut_str = (request.POST.get(
                    f"containers[{i}][bags_cut]") or "").strip()

                if not tonnage_str:
                    messages.error(
                        request, f"Container {container_number}: Tonnage is required.")
                    raise transaction.TransactionManagementError(
                        "Validation error")

                if not bags_cut_str:
                    messages.error(
                        request, f"Container {container_number}: Bags cut is required.")
                    raise transaction.TransactionManagementError(
                        "Validation error")

                try:
                    tonnage = Decimal(tonnage_str).quantize(Decimal("0.001"))
                    bags_cut = int(bags_cut_str)
                    if tonnage < 0 or bags_cut < 0:
                        raise ValueError
                except (InvalidOperation, ValueError):
                    messages.error(
                        request, f"Container {container_number}: Invalid tonnage or bags cut value.")
                    raise transaction.TransactionManagementError(
                        "Validation error")

                bags_val = bags_cut
                ton_val = tonnage

            else:
                bags_raw = (request.POST.get(
                    f"containers[{i}][bags]") or "").strip()
                tonnage_raw = (request.POST.get(
                    f"containers[{i}][tonnage]") or "").strip()

                if not bags_raw:
                    messages.error(
                        request, f"Container {container_number}: Bags is required.")
                    raise transaction.TransactionManagementError(
                        "Validation error")

                try:
                    bags = int(Decimal(bags_raw))
                    if bags < 0:
                        raise ValueError
                except (InvalidOperation, ValueError):
                    messages.error(
                        request, f"Container {container_number}: Invalid bags value.")
                    raise transaction.TransactionManagementError(
                        "Validation error")

                try:
                    if tonnage_raw:
                        tonnage = Decimal(tonnage_raw).quantize(
                            Decimal("0.001"))
                    else:
                        tonnage = (Decimal(bags) / Decimal("16")
                                   ).quantize(Decimal("0.001"))
                    if tonnage < 0:
                        raise ValueError
                except (InvalidOperation, ValueError):
                    messages.error(
                        request, f"Container {container_number}: Invalid tonnage value.")
                    raise transaction.TransactionManagementError(
                        "Validation error")

                bags_val = bags
                ton_val = tonnage

            calculated_bags += int(bags_val)
            calculated_tonnage += ton_val

            # Update existing container if possible, else create new.
            if cid and cid in existing_by_id:
                cobj = existing_by_id[cid]
                used_ids.add(cid)

                cobj.container_number = container_number
                cobj.seal_number = seal_number
                cobj.tonnage = ton_val

                if tally.tally_type == "BULK":
                    cobj.bags_cut = int(bags_val)
                    cobj.bags = int(bags_val)
                else:
                    cobj.bags_cut = None
                    cobj.bags = int(bags_val)

                cobj.save()

            else:
                # New row added in edit mode
                TallyContainer.objects.create(
                    tally=tally,
                    container_number=container_number,
                    seal_number=seal_number,
                    tonnage=ton_val,
                    bags_cut=int(
                        bags_val) if tally.tally_type == "BULK" else None,
                    bags=int(bags_val),
                )

        # Validate totals like your create views do
        if total_bags_form and total_bags_form != calculated_bags:
            messages.error(
                request, "Totals mismatch: TOTAL BAGS does not equal sum of container bags.")
            raise transaction.TransactionManagementError("Validation error")

        # Allow blank total_tonnage on form, but if provided, enforce match
        if total_tonnage_form != Decimal("0.000"):
            if total_tonnage_form.quantize(Decimal("0.001")) != calculated_tonnage.quantize(Decimal("0.001")):
                messages.error(
                    request, "Totals mismatch: TOTAL TONNAGE does not equal sum of container tonnage.")
                raise transaction.TransactionManagementError(
                    "Validation error")

        tally.total_bags = calculated_bags
        tally.total_tonnage = calculated_tonnage.quantize(Decimal("0.001"))
        tally.updated_by = request.user
        tally.save()

        # Delete containers removed from the form
        for c in existing:
            if str(c.id) not in used_ids:
                c.delete()

    messages.success(
        request,
        f"✓ Tally updated by {request.user.first_name} {request.user.last_name}"
    )
    return redirect("my_tallies")


# ── Tally Approval Workflow ────────────────────────────────────────

@login_required(login_url='login')
def tally_delete(request, pk):
    """Delete a tally - allowed for creators (non-approved) or supervisors (any status)."""
    from apps.operations.permissions import is_terminal_supervisor

    # Check if user is supervisor or creator
    is_supervisor = is_terminal_supervisor(request.user)

    if is_supervisor:
        # Supervisors can delete any tally
        tally = get_object_or_404(TallyInfo, pk=pk)
    else:
        # Regular users can only delete their own non-approved tallies
        tally = get_object_or_404(TallyInfo, pk=pk, created_by=request.user)
        if tally.status == 'APPROVED':
            messages.error(
                request, "Approved tallies cannot be deleted. Contact your supervisor.")
            return redirect("my_tallies")

    if request.method == 'POST':
        tally_number = tally.tally_number
        sd_number = tally.sd_number
        tally.delete()
        messages.success(
            request, f"Tally {tally_number} for SD {sd_number} has been deleted successfully.")

        # Redirect based on user role
        if is_supervisor:
            return redirect("pending_tallies")
        else:
            return redirect("my_tallies")

    return render(request, 'tally_details/tally_confirm_delete.html', {
        'tally': tally,
    })
