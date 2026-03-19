"""Tally creation views.

Mechanically extracted from views_old.py to keep behavior unchanged.
"""

from apps.operations.models import get_current_crop_year_choices, SDRecord
from ..models import TallyContainer, TallyInfo, Terminal
import datetime
import re
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
import logging

from apps.tally.views._old_shared import _safe_reverse

logger = logging.getLogger(__name__)


@login_required(login_url='login')
def loading(request):
    """
    Initial loading type selection page.

    User chooses between BULK or STRAIGHT loading. Selection stored in
    session and determines which form to show next.

    Returns:
        GET: Renders loading type selection page
        POST: Stores selection in session and redirects to appropriate form
    """
    if request.method == "POST":
        loading_type = request.POST.get("loading_type", "").strip()

        if loading_type not in ["BULK", "STRAIGHT"]:
            messages.error(request, "Invalid loading type selected.")
            return redirect("loading")

        request.session["loading_type"] = loading_type

        if loading_type == "BULK":
            return redirect("bulk")
        return redirect("straight_loading_options")

    request.session.pop("loading_type", None)
    request.session.pop("straight_type", None)
    return render(request, "loading/loading.html")


@login_required(login_url='login')
def straight_loading_options(request):
    """
    Straight loading sub-type selection page.

    User chooses between:
    - STRAIGHT_20FT: 20-foot containers
    - STRAIGHT_40FT: 40-foot containers
    - JAPAN_STRAIGHT_40FT: Japan-specific 40-foot containers

    Requires: loading_type=STRAIGHT in session

    Returns:
        GET: Renders straight loading options page
        POST: Stores selection and redirects to appropriate form
    """
    if request.session.get("loading_type") != "STRAIGHT":
        messages.warning(request, "Please select loading type first.")
        return redirect("loading")

    if request.method == "POST":
        straight_type = request.POST.get("straight_type", "").strip()

        allowed = ["JAPAN_STRAIGHT_40FT", "STRAIGHT_40FT", "STRAIGHT_20FT"]
        if straight_type not in allowed:
            messages.error(request, "Invalid straight loading type.")
            return redirect("straight_loading_options")

        request.session["straight_type"] = straight_type

        redirect_map = {
            "STRAIGHT_40FT": "normal_straight",
            "JAPAN_STRAIGHT_40FT": "japan",
            "STRAIGHT_20FT": "straight_20",
        }
        return redirect(redirect_map.get(straight_type, "straight_loading_options"))

    return render(request, "straight_loading/straight_loading_options.html")


@login_required(login_url='login')
def bulk(request):
    """
    Create bulk loading tally with container details.

    Features:
    - Bulk loading type (loose bags loaded into containers)
    - Auto-generates unique tally number (YYYYMMDD + sequence)
    - Validates all required fields (crop year, SD, MK, vessel, etc.)
    - Collects container data (number, seal, tonnage, bags cut)
    - Calculates totals (bags, tonnage) from container entries
    - Tracks expected vs actual bags (bags saved/lost)
    - Supports multiple superintendents and clerks
    - Links to terminal for supervisor routing
    - Auto-links to SD record when available

    Validation:
    - All required fields must be filled
    - At least one clerk name required
    - At least one container required
    - Superintendent name required if type != NONE
    - Bag counts cannot be negative
    - Tonnage and bags cut required for each container

    Security:
    - All authenticated users can create tallies
    - Tally number uniqueness enforced with collision detection

    Permissions: All authenticated users

    Returns:
        GET: Renders bulk loading form
        POST: Creates tally and redirects to success page
    """
    # Prepare context for all renders
    terminals = Terminal.objects.all()
    crop_year_choices = get_current_crop_year_choices()
    all_sd_numbers = SDRecord.objects.values_list(
        'sd_number', flat=True).distinct()
    context = {
        'terminals': terminals,
        'crop_year_choices': crop_year_choices,
        'all_sd_numbers': all_sd_numbers,
    }

    if request.method == "POST":
        crop_year = request.POST.get("crop_year", "").strip()
        sd_number = request.POST.get("sd_number", "").strip()
        mk_number = request.POST.get("mk_number", "").strip()
        agent = request.POST.get("agent", "").strip()
        vessel = request.POST.get("vessel", "").strip()
        destination = request.POST.get("destination", "").strip()
        terminal_id = request.POST.get("terminal", "").strip()
        loading_date_str = request.POST.get("loading_date", "").strip()
        marks_numbers = request.POST.get("marks_and_numbers", "").strip()
        cocoa_type = request.POST.get("cocoa_type", "").strip()
        superintendent_type = request.POST.get(
            "superintendent_type", "NONE").strip()

        required_fields = {
            "crop_year": crop_year,
            "sd_number": sd_number,
            "mk_number": mk_number,
            "vessel": vessel,
            "destination": destination,
            "terminal": terminal_id,
            "loading_date": loading_date_str,
        }

        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            messages.error(
                request, f"Missing required info: {', '.join(missing)}")
            return render(request, "bulk/bulk_loading.html", context)

        try:
            loading_date = datetime.datetime.strptime(
                loading_date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, "bulk/bulk_loading.html", context)

        superintendent_names = [
            v.strip() for v in request.POST.getlist("s_name") if v.strip()]
        clerk_names = [v.strip()
                       for v in request.POST.getlist("clerk_name") if v.strip()]

        if not clerk_names:
            messages.error(request, "At least one clerk name is required.")
            return render(request, "bulk/bulk_loading.html", context)

        if superintendent_type != "NONE" and not superintendent_names:
            messages.error(request, "Name required please")
            return render(request, "bulk/bulk_loading.html", context)

        try:
            expected_bags = int(request.POST.get("expected_bags", 0))
            actual_bags = int(request.POST.get("actual_bags", 0))
            if expected_bags < 0 or actual_bags < 0:
                raise ValueError("Bag counts cannot be negative")
            bags_saved = expected_bags - actual_bags
        except (ValueError, TypeError) as err:
            messages.error(request, f"Invalid bag count: {str(err)}")
            return render(request, "bulk/bulk_loading.html", context)

        try:
            total_bags_form = int(request.POST.get("total_bags", 0))
            total_tonnage_form = Decimal(
                request.POST.get("total_tonnage", "0"))
        except (ValueError, InvalidOperation):
            messages.error(request, "Invalid total bags or tonnage values.")
            return render(request, "bulk/bulk_loading.html", context)

        current_date = datetime.date.today()
        date_string = current_date.strftime("%Y%m%d")

        # System-wide count ensures uniqueness across all users on same day
        today_tallies = TallyInfo.objects.filter(
            date_created__date=current_date).count()
        tally_count = today_tallies + 1
        tally_number = int(f"{date_string}{tally_count}")

        while TallyInfo.objects.filter(tally_number=tally_number).exists():
            tally_count += 1
            tally_number = int(f"{date_string}{tally_count}")

        container_pattern = re.compile(r"^containers\[(\d+)\]\[")
        container_indices = set()

        for key in request.POST.keys():
            match = container_pattern.match(key)
            if match:
                container_indices.add(int(match.group(1)))

        for key in request.FILES.keys():
            match = container_pattern.match(key)
            if match:
                container_indices.add(int(match.group(1)))

        if not container_indices:
            messages.error(request, "At least one container is required.")
            return render(request, "bulk/bulk_loading.html", context)

        containers_data = []
        calculated_bags = 0
        calculated_tonnage = Decimal("0")
        max_size = 5 * 1024 * 1024

        for i in sorted(container_indices):
            container_number = request.POST.get(
                f"containers[{i}][container_number]", "").strip()
            seal_number = request.POST.get(
                f"containers[{i}][seal_number]", "").strip()
            tonnage_str = request.POST.get(
                f"containers[{i}][tonnage]", "").strip()
            bags_cut_str = request.POST.get(
                f"containers[{i}][bags_cut]", "").strip()

            if not container_number:
                continue

            if not seal_number:
                messages.error(
                    request, f"Container {container_number}: Seal number is required.")
                return render(request, "bulk/bulk_loading.html", context)

            if not tonnage_str:
                messages.error(
                    request, f"Container {container_number}: Tonnage is required.")
                return render(request, "bulk/bulk_loading.html", context)

            if not bags_cut_str:
                messages.error(
                    request, f"Container {container_number}: Bags cut is required.")
                return render(request, "bulk/bulk_loading.html", context)

            try:
                tonnage = Decimal(tonnage_str).quantize(Decimal("0.001"))
                bags_cut = int(bags_cut_str)
                if tonnage < 0 or bags_cut < 0:
                    raise ValueError("Values cannot be negative")
            except (ValueError, InvalidOperation):
                messages.error(
                    request, f"Container {container_number}: Invalid tonnage or bags cut value.")
                return render(request, "bulk/bulk_loading.html", context)

            calculated_bags += bags_cut
            calculated_tonnage += tonnage

            containers_data.append(
                {
                    "container_number": container_number,
                    "seal_number": seal_number,
                    "tonnage": tonnage,
                    "bags_cut": bags_cut,
                }
            )

        if not containers_data:
            messages.error(
                request, "At least one complete container is required.")
            return render(request, "bulk/bulk_loading.html", context)

        total_bags = calculated_bags if calculated_bags != total_bags_form else total_bags_form
        total_tonnage = (
            calculated_tonnage
            if abs(calculated_tonnage - total_tonnage_form) > Decimal("0.01")
            else total_tonnage_form
        )

        try:
            terminal_obj = Terminal.objects.get(id=terminal_id)
        except (Terminal.DoesNotExist, ValueError, TypeError):
            messages.error(request, "Invalid terminal selected.")
            return render(request, "bulk/bulk_loading.html", context)

        with transaction.atomic():
            tally = TallyInfo.objects.create(
                created_by=request.user,
                tally_number=tally_number,
                tally_type="BULK",
                crop_year=crop_year,
                sd_number=sd_number,
                mk_number=mk_number,
                agent=agent,
                vessel=vessel,
                destination=destination,
                terminal_name=terminal_obj.name,
                terminal=terminal_obj,
                loading_type="BULK",
                loading_date=loading_date,
                marks_and_numbers=marks_numbers,
                cocoa_type=cocoa_type,
                superintendent_type=superintendent_type,
                superintendent_name=superintendent_names,
                clerk_name=clerk_names,
                expected_bags=expected_bags,
                actual_bags=actual_bags,
                bags_saved=bags_saved,
                total_bags=total_bags,
                total_tonnage=total_tonnage,
            )

            for container_data in containers_data:
                TallyContainer.objects.create(
                    tally=tally,
                    container_number=container_data["container_number"],
                    seal_number=container_data["seal_number"],
                    tonnage=container_data["tonnage"],
                    bags_cut=container_data["bags_cut"],
                    bags=container_data["bags_cut"],
                )

        messages.success(
            request,
            f"✓ Bulk loading tally #{tally_number} created successfully"
        )
        return redirect("tally_success")

    terminals = Terminal.objects.all()
    crop_year_choices = get_current_crop_year_choices()
    all_sd_numbers = SDRecord.objects.values_list(
        'sd_number', flat=True).distinct()

    return render(request, "bulk/bulk_loading.html", {
        'terminals': terminals,
        'crop_year_choices': crop_year_choices,
        'all_sd_numbers': all_sd_numbers,
    })


@login_required(login_url='login')
def normal_straight(request):
    """
    Create straight 40ft loading tally with container details.

    Features:
    - Straight loading type (pre-stuffed 40ft containers)
    - Auto-generates unique tally number (YYYYMMDD + sequence)
    - Validates all required fields (crop year, SD, MK, vessel, etc.)
    - Collects container data (number, seal, bags, tonnage)
    - Auto-calculates tonnage from bags if not provided (bags / 16)
    - Validates totals match sum of containers
    - Supports multiple superintendents and clerks
    - Links to terminal for supervisor routing
    - Auto-links to SD record when available

    Validation:
    - All required fields must be filled
    - At least one clerk name required
    - At least one container required
    - Superintendent name required if type != NONE
    - Bags and seal number required for each container
    - Total bags must equal sum of container bags
    - Total tonnage must equal sum of container tonnage

    Security:
    - All authenticated users can create tallies
    - Tally number uniqueness enforced with collision detection

    Permissions: All authenticated users

    Returns:
        GET: Renders straight 40ft loading form
        POST: Creates tally and redirects to success page
    """
    template_name = "straight_loading/40_straight_loading.html"

    # Prepare context for all renders
    terminals = Terminal.objects.all()
    crop_year_choices = get_current_crop_year_choices()
    all_sd_numbers = SDRecord.objects.values_list(
        'sd_number', flat=True).distinct()
    context = {
        'terminals': terminals,
        'crop_year_choices': crop_year_choices,
        'all_sd_numbers': all_sd_numbers,
    }

    if request.method == "GET":
        return render(request, template_name, context)

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
    dry_bags = request.POST.get("dry_bags", "").strip() or None

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
        return render(request, template_name, context)

    try:
        loading_date = datetime.datetime.strptime(
            loading_date_raw, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid date format")
        return render(request, template_name, context)

    superintendent_names = [v.strip()
                            for v in request.POST.getlist("s_name") if v.strip()]
    clerk_names = [v.strip()
                   for v in request.POST.getlist("clerk_name") if v.strip()]

    if not clerk_names:
        messages.error(request, "Enter at least 1 clerk")
        return render(request, template_name, context)

    if superintendent_type != "NONE" and not superintendent_names:
        messages.error(request, "Superintendent name is required")
        return render(request, template_name, context)

    total_bags_form_raw = request.POST.get("total_bags", "0").strip()
    total_tonnage_form_raw = request.POST.get("total_tonnage", "0").strip()

    try:
        total_bags_form = int(Decimal(total_bags_form_raw or 0))
    except (InvalidOperation, ValueError):
        total_bags_form = 0

    try:
        total_tonnage_form = Decimal(total_tonnage_form_raw or "0")
    except (InvalidOperation, ValueError):
        total_tonnage_form = Decimal("0")

    container_pattern = re.compile(r"^containers\[(\d+)\]\[")
    container_indices = set()

    for key in request.POST.keys():
        m = container_pattern.match(key)
        if m:
            container_indices.add(int(m.group(1)))

    for key in request.FILES.keys():
        m = container_pattern.match(key)
        if m:
            container_indices.add(int(m.group(1)))

    if not container_indices:
        messages.error(request, "At least one container is required.")
        return render(request, template_name, context)

    containers_data = []
    calculated_bags = 0
    calculated_tonnage = Decimal("0")
    max_size = 5 * 1024 * 1024

    for i in sorted(container_indices):
        container_number = request.POST.get(
            f"containers[{i}][container_number]", "").strip()
        seal_number = request.POST.get(
            f"containers[{i}][seal_number]", "").strip()
        bags_raw = request.POST.get(f"containers[{i}][bags]", "").strip()
        tonnage_raw = request.POST.get(f"containers[{i}][tonnage]", "").strip()

        if not container_number:
            continue

        if not seal_number:
            messages.error(
                request, f"Container {container_number}: Seal number is required.")
            return render(request, template_name, context)

        if not bags_raw:
            messages.error(
                request, f"Container {container_number}: Bags is required.")
            return render(request, template_name, context)

        try:
            bags = int(Decimal(bags_raw))
            if bags < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(
                request, f"Container {container_number}: Invalid bags value.")
            return render(request, template_name, context)

        try:
            if tonnage_raw:
                tonnage = Decimal(tonnage_raw).quantize(Decimal("0.001"))
            else:
                tonnage = (Decimal(bags) / Decimal("16")
                           ).quantize(Decimal("0.001"))
            if tonnage < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(
                request, f"Container {container_number}: Invalid tonnage value.")
            return render(request, template_name, context)

        containers_data.append(
            {
                "container_number": container_number,
                "seal_number": seal_number,
                "bags": bags,
                "tonnage": tonnage,
            }
        )

        calculated_bags += bags
        calculated_tonnage += tonnage

    if not containers_data:
        messages.error(request, "At least one complete container is required.")
        return render(request, template_name, context)

    current_date = datetime.date.today()
    date_string = current_date.strftime("%Y%m%d")
    # System-wide count ensures uniqueness across all users on same day
    tally_count = TallyInfo.objects.filter(
        date_created__date=current_date).count() + 1
    tally_number = int(f"{date_string}{tally_count}")

    while TallyInfo.objects.filter(tally_number=tally_number).exists():
        tally_count += 1
        tally_number = int(f"{date_string}{tally_count}")

    if total_bags_form and total_bags_form != calculated_bags:
        messages.error(
            request, "Totals mismatch: TOTAL BAGS does not equal sum of container bags.")
        return render(request, template_name, context)

    if total_tonnage_form and total_tonnage_form.quantize(Decimal("0.001")) != calculated_tonnage.quantize(Decimal("0.001")):
        messages.error(
            request, "Totals mismatch: TOTAL TONNAGE does not equal sum of container tonnage.")
        return render(request, template_name, context)

    try:
        terminal_obj = Terminal.objects.get(id=terminal_id)
    except (Terminal.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Invalid terminal selected.")
        return render(request, template_name, context)

    tally = TallyInfo.objects.create(
        created_by=request.user,
        tally_number=tally_number,
        tally_type="STRAIGHT_40FT",
        crop_year=crop_year,
        sd_number=sd_number,
        mk_number=mk_number,
        agent=agent,
        vessel=vessel,
        destination=destination,
        terminal_name=terminal_obj.name,
        terminal=terminal_obj,
        loading_type="STRAIGHT",
        straight_type="STRAIGHT_40FT",
        loading_date=loading_date,
        marks_and_numbers=marks_and_numbers or "GCB",
        cocoa_type=cocoa_type,
        superintendent_type=superintendent_type,
        superintendent_name=superintendent_names,
        clerk_name=clerk_names,
        dry_bags=dry_bags,
        total_bags=calculated_bags,
        total_tonnage=calculated_tonnage.quantize(Decimal("0.001")),
    )

    for c in containers_data:
        TallyContainer.objects.create(tally=tally, **c)

    messages.success(
        request,
        f"✓ Straight loading tally #{tally_number} created successfully"
    )
    return redirect("tally_success")


@login_required(login_url='login')
def japan(request):
    """
    Create Japan straight 40ft loading tally with seller codes and color tags.

    Features:
    - Japan-specific straight loading type (40ft containers)
    - Auto-generates unique tally number (YYYYMMDD + sequence)
    - Validates all required fields (crop year, SD, MK, vessel, etc.)
    - Collects container data (number, seal, bags, tonnage)
    - Auto-calculates tonnage from bags if not provided (bags / 16)
    - Validates totals match sum of containers
    - Supports seller codes and color tag entries (Japan-specific)
    - Supports multiple superintendents and clerks
    - Links to terminal for supervisor routing
    - Auto-links to SD record when available

    Validation:
    - All required fields must be filled
    - At least one clerk name required
    - At least one container required
    - Superintendent name required if type != NONE
    - Bags and seal number required for each container
    - Total bags must equal sum of container bags
    - Total tonnage must equal sum of container tonnage

    Security:
    - All authenticated users can create tallies
    - Tally number uniqueness enforced with collision detection

    Permissions: All authenticated users

    Returns:
        GET: Renders Japan straight loading form
        POST: Creates tally and redirects to success page
    """
    template_name = "straight_loading/japan_straight_loading.html"

    # Prepare context for all renders
    terminals = Terminal.objects.all()
    crop_year_choices = get_current_crop_year_choices()
    all_sd_numbers = SDRecord.objects.values_list(
        'sd_number', flat=True).distinct()
    context = {
        'terminals': terminals,
        'crop_year_choices': crop_year_choices,
        'all_sd_numbers': all_sd_numbers,
    }

    if request.method == "GET":
        return render(request, template_name, context)

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
    dry_bags = request.POST.get("dry_bags", "").strip() or None

    seller_codes = [v.strip()
                    for v in request.POST.getlist("seller_codes") if v.strip()]
    color_tag_entries = [v.strip() for v in request.POST.getlist(
        "color_tag_entries") if v.strip()]

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
        return render(request, template_name, context)

    try:
        loading_date = datetime.datetime.strptime(
            loading_date_raw, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid date format")
        return render(request, template_name, context)

    superintendent_names = [v.strip()
                            for v in request.POST.getlist("s_name") if v.strip()]
    clerk_names = [v.strip()
                   for v in request.POST.getlist("clerk_name") if v.strip()]

    if not clerk_names:
        messages.error(request, "Enter at least 1 clerk")
        return render(request, template_name, context)

    if superintendent_type != "NONE" and not superintendent_names:
        messages.error(request, "Superintendent name is required")
        return render(request, template_name, context)

    total_bags_form_raw = request.POST.get("total_bags", "0").strip()
    total_tonnage_form_raw = request.POST.get("total_tonnage", "0").strip()

    try:
        total_bags_form = int(Decimal(total_bags_form_raw or "0"))
    except (InvalidOperation, ValueError):
        total_bags_form = 0

    try:
        total_tonnage_form = Decimal(
            total_tonnage_form_raw or "0").quantize(Decimal("0.001"))
    except (InvalidOperation, ValueError):
        total_tonnage_form = Decimal("0.000")

    container_pattern = re.compile(r"^containers\[(\d+)\]\[")
    container_indices = set()

    for key in request.POST.keys():
        m = container_pattern.match(key)
        if m:
            container_indices.add(int(m.group(1)))

    for key in request.FILES.keys():
        m = container_pattern.match(key)
        if m:
            container_indices.add(int(m.group(1)))

    if not container_indices:
        messages.error(request, "At least one container is required.")
        return render(request, template_name, context)

    containers_data = []
    calculated_bags = 0
    calculated_tonnage = Decimal("0.000")
    max_size = 5 * 1024 * 1024

    for i in sorted(container_indices):
        container_number = request.POST.get(
            f"containers[{i}][container_number]", "").strip()
        seal_number = request.POST.get(
            f"containers[{i}][seal_number]", "").strip()
        bags_raw = request.POST.get(f"containers[{i}][bags]", "").strip()
        tonnage_raw = request.POST.get(f"containers[{i}][tonnage]", "").strip()

        if not container_number:
            continue

        if not seal_number:
            messages.error(
                request, f"Container {container_number}: Seal number is required.")
            return render(request, template_name, context)

        if not bags_raw:
            messages.error(
                request, f"Container {container_number}: Bags is required.")
            return render(request, template_name, context)

        try:
            bags = int(Decimal(bags_raw))
            if bags < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(
                request, f"Container {container_number}: Invalid bags value.")
            return render(request, template_name, context)

        try:
            if tonnage_raw:
                tonnage = Decimal(tonnage_raw).quantize(Decimal("0.001"))
            else:
                tonnage = (Decimal(bags) / Decimal("16")
                           ).quantize(Decimal("0.001"))
            if tonnage < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(
                request, f"Container {container_number}: Invalid tonnage value.")
            return render(request, template_name, context)

        containers_data.append(
            {
                "container_number": container_number,
                "seal_number": seal_number,
                "bags": bags,
                "tonnage": tonnage,
            }
        )

        calculated_bags += bags
        calculated_tonnage += tonnage

    if not containers_data:
        messages.error(request, "At least one complete container is required.")
        return render(request, template_name, context)

    current_date = datetime.date.today()
    date_string = current_date.strftime("%Y%m%d")
    # System-wide count ensures uniqueness across all users on same day
    tally_count = TallyInfo.objects.filter(
        date_created__date=current_date).count() + 1
    tally_number = int(f"{date_string}{tally_count}")

    while TallyInfo.objects.filter(tally_number=tally_number).exists():
        tally_count += 1
        tally_number = int(f"{date_string}{tally_count}")

    if total_bags_form and total_bags_form != calculated_bags:
        messages.error(
            request, "Totals mismatch: TOTAL BAGS does not equal sum of container bags.")
        return render(request, template_name, context)

    if total_tonnage_form != Decimal("0.000"):
        if total_tonnage_form.quantize(Decimal("0.001")) != calculated_tonnage.quantize(Decimal("0.001")):
            messages.error(
                request, "Totals mismatch: TOTAL TONNAGE does not equal sum of container tonnage.")
            return render(request, template_name, context)

    try:
        terminal_obj = Terminal.objects.get(id=terminal_id)
    except (Terminal.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Invalid terminal selected.")
        return render(request, template_name, context)

    with transaction.atomic():
        tally = TallyInfo.objects.create(
            created_by=request.user,
            tally_number=tally_number,
            tally_type="JAPAN_STRAIGHT_40FT",
            crop_year=crop_year,
            sd_number=sd_number,
            mk_number=mk_number,
            agent=agent,
            vessel=vessel,
            destination=destination,
            terminal_name=terminal_obj.name,
            terminal=terminal_obj,
            loading_type="STRAIGHT",
            straight_type="JAPAN_STRAIGHT_40FT",
            loading_date=loading_date,
            marks_and_numbers=marks_and_numbers or "GCB",
            cocoa_type=cocoa_type,
            superintendent_type=superintendent_type,
            superintendent_name=superintendent_names,
            clerk_name=clerk_names,
            dry_bags=dry_bags,
            total_bags=calculated_bags,
            total_tonnage=calculated_tonnage.quantize(Decimal("0.001")),
            seller_codes=seller_codes,
            color_tag_entries=color_tag_entries,
        )

        for c in containers_data:
            TallyContainer.objects.create(tally=tally, **c)

    messages.success(
        request,
        f"✓ Japan straight loading tally #{tally_number} created successfully"
    )
    return redirect("tally_success")


@login_required(login_url='login')
def straight_20(request):
    """
    Create straight 20ft loading tally with container details.

    Features:
    - Straight loading type (pre-stuffed 20ft containers)
    - Auto-generates unique tally number (YYYYMMDD + sequence)
    - Validates all required fields (crop year, SD, MK, vessel, etc.)
    - Collects container data (number, seal, bags, tonnage)
    - Auto-calculates tonnage from bags if not provided (bags / 16)
    - Validates totals match sum of containers
    - Supports multiple superintendents and clerks
    - Links to terminal for supervisor routing
    - Auto-links to SD record when available

    Validation:
    - All required fields must be filled
    - At least one clerk name required
    - At least one container required
    - Superintendent name required if type != NONE
    - Bags and seal number required for each container
    - Total bags must equal sum of container bags
    - Total tonnage must equal sum of container tonnage

    Security:
    - All authenticated users can create tallies
    - Tally number uniqueness enforced with collision detection

    Permissions: All authenticated users

    Returns:
        GET: Renders straight 20ft loading form
        POST: Creates tally and redirects to success page
    """
    template_name = "straight_loading/20_straight_loading.html"

    # Prepare context for all renders
    terminals = Terminal.objects.all()
    crop_year_choices = get_current_crop_year_choices()
    all_sd_numbers = SDRecord.objects.values_list(
        'sd_number', flat=True).distinct()
    context = {
        'terminals': terminals,
        'crop_year_choices': crop_year_choices,
        'all_sd_numbers': all_sd_numbers,
    }

    if request.method == "GET":
        return render(request, template_name, context)

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
    dry_bags = request.POST.get("dry_bags", "").strip() or None

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
        return render(request, template_name, context)

    try:
        loading_date = datetime.datetime.strptime(
            loading_date_raw, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid date format")
        return render(request, template_name, context)

    superintendent_names = [v.strip()
                            for v in request.POST.getlist("s_name") if v.strip()]
    clerk_names = [v.strip()
                   for v in request.POST.getlist("clerk_name") if v.strip()]

    if not clerk_names:
        messages.error(request, "Enter at least 1 clerk")
        return render(request, template_name, context)

    if superintendent_type != "NONE" and not superintendent_names:
        messages.error(request, "Superintendent name is required")
        return render(request, template_name, context)

    total_bags_form_raw = request.POST.get("total_bags", "0").strip()
    total_tonnage_form_raw = request.POST.get("total_tonnage", "0").strip()

    try:
        total_bags_form = int(Decimal(total_bags_form_raw or "0"))
    except (InvalidOperation, ValueError):
        total_bags_form = 0

    try:
        total_tonnage_form = Decimal(
            total_tonnage_form_raw or "0").quantize(Decimal("0.001"))
    except (InvalidOperation, ValueError):
        total_tonnage_form = Decimal("0.000")

    container_pattern = re.compile(r"^containers\[(\d+)\]\[")
    container_indices = set()

    for key in request.POST.keys():
        m = container_pattern.match(key)
        if m:
            container_indices.add(int(m.group(1)))

    for key in request.FILES.keys():
        m = container_pattern.match(key)
        if m:
            container_indices.add(int(m.group(1)))

    if not container_indices:
        messages.error(request, "At least one container is required.")
        return render(request, template_name, context)

    containers_data = []
    calculated_bags = 0
    calculated_tonnage = Decimal("0.000")
    max_size = 5 * 1024 * 1024

    for i in sorted(container_indices):
        container_number = request.POST.get(
            f"containers[{i}][container_number]", "").strip()
        seal_number = request.POST.get(
            f"containers[{i}][seal_number]", "").strip()
        bags_raw = request.POST.get(f"containers[{i}][bags]", "").strip()
        tonnage_raw = request.POST.get(f"containers[{i}][tonnage]", "").strip()

        if not container_number:
            continue

        if not seal_number:
            messages.error(
                request, f"Container {container_number}: Seal number is required.")
            return render(request, template_name, context)

        if not bags_raw:
            messages.error(
                request, f"Container {container_number}: Bags is required.")
            return render(request, template_name, context)

        try:
            bags = int(Decimal(bags_raw))
            if bags < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(
                request, f"Container {container_number}: Invalid bags value.")
            return render(request, template_name, context)

        try:
            if tonnage_raw:
                tonnage = Decimal(tonnage_raw).quantize(Decimal("0.001"))
            else:
                tonnage = (Decimal(bags) / Decimal("16")
                           ).quantize(Decimal("0.001"))
            if tonnage < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(
                request, f"Container {container_number}: Invalid tonnage value.")
            return render(request, template_name, context)

        containers_data.append(
            {
                "container_number": container_number,
                "seal_number": seal_number,
                "bags": bags,
                "tonnage": tonnage,
            }
        )

        calculated_bags += bags
        calculated_tonnage += tonnage

    if not containers_data:
        messages.error(request, "At least one complete container is required.")
        return render(request, template_name, context)

    current_date = datetime.date.today()
    date_string = current_date.strftime("%Y%m%d")
    # System-wide count ensures uniqueness across all users on same day
    tally_count = TallyInfo.objects.filter(
        date_created__date=current_date).count() + 1
    tally_number = int(f"{date_string}{tally_count}")

    while TallyInfo.objects.filter(tally_number=tally_number).exists():
        tally_count += 1
        tally_number = int(f"{date_string}{tally_count}")

    if total_bags_form and total_bags_form != calculated_bags:
        messages.error(
            request, "Totals mismatch: TOTAL BAGS does not equal sum of container bags.")
        return render(request, template_name, context)

    if total_tonnage_form != Decimal("0.000"):
        if total_tonnage_form.quantize(Decimal("0.001")) != calculated_tonnage.quantize(Decimal("0.001")):
            messages.error(
                request, "Totals mismatch: TOTAL TONNAGE does not equal sum of container tonnage.")
            return render(request, template_name, context)

    try:
        terminal_obj = Terminal.objects.get(id=terminal_id)
    except (Terminal.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Invalid terminal selected.")
        return render(request, template_name, context)

    with transaction.atomic():
        tally = TallyInfo.objects.create(
            created_by=request.user,
            tally_number=tally_number,
            tally_type="STRAIGHT_20FT",
            crop_year=crop_year,
            sd_number=sd_number,
            mk_number=mk_number,
            agent=agent,
            vessel=vessel,
            destination=destination,
            terminal_name=terminal_obj.name,
            terminal=terminal_obj,
            loading_type="STRAIGHT",
            straight_type="STRAIGHT_20FT",
            loading_date=loading_date,
            marks_and_numbers=marks_and_numbers or "GCB",
            cocoa_type=cocoa_type,
            superintendent_type=superintendent_type,
            superintendent_name=superintendent_names,
            clerk_name=clerk_names,
            dry_bags=dry_bags,
            total_bags=calculated_bags,
            total_tonnage=calculated_tonnage.quantize(Decimal("0.001")),
        )

        for c in containers_data:
            TallyContainer.objects.create(tally=tally, **c)

    messages.success(
        request,
        f"✓ 20ft straight loading tally #{tally_number} created successfully"
    )
    return redirect("tally_success")


@login_required(login_url='login')
def tally_success(request):
    """
    Display success page after tally creation with download links.

    Features:
    - Shows latest created tally details
    - Provides download links (Excel, PDF, view)
    - Lists 10 most recent tallies with quick access links
    - Links to create new tally or view all tallies

    Permissions: All authenticated users (shows only their own tallies)

    Returns:
        Renders tally_success.html with latest tally and recent tallies list
    """
    latest_tally = TallyInfo.objects.filter(
        created_by=request.user).order_by("-date_created").first()
    recent_qs = TallyInfo.objects.filter(
        created_by=request.user).order_by("-date_created")[:10]

    recent_tallies = []
    for t in recent_qs:
        recent_tallies.append(
            {
                "sd_number": t.sd_number,
                "mk_number": t.mk_number,
                "vessel": t.vessel,
                "destination": t.destination,
                "loading_date": t.loading_date,
                "view_url": _safe_reverse("tally_view", pk=t.pk),
                "excel_url": _safe_reverse("tally_excel", pk=t.pk),
                "pdf_url": _safe_reverse("tally_pdf", pk=t.pk),
            }
        )

    context = {
        "tally": latest_tally,
        "latest_tally": latest_tally,
        "latest_view_url": _safe_reverse("tally_view", pk=latest_tally.pk) if latest_tally else "#",
        "latest_excel_url": _safe_reverse("tally_excel", pk=latest_tally.pk) if latest_tally else "#",
        "latest_pdf_url": _safe_reverse("tally_pdf", pk=latest_tally.pk) if latest_tally else "#",
        "new_tally_url": _safe_reverse("loading"),
        "view_all_url": _safe_reverse("my_tallies"),
        "recent_tallies": recent_tallies,
    }

    return render(request, "tally_details/tally_success.html", context)


@login_required(login_url='login')
def new_tally(request):
    """
    Redirect to loading type selection page.

    Simple redirect view for creating a new tally.
    Redirects to the loading type selection page where user chooses BULK or STRAIGHT.

    Permissions: All authenticated users

    Returns:
        Redirects to loading type selection page
    """
    return redirect("loading")
