from django import template
from decimal import Decimal
from apps.operations.permissions import (
    can_manage_schedules,
    can_manage_sd_records,
    is_terminal_supervisor,
)
from apps.ebooking.permissions import can_manage_bookings
from apps.declaration.permissions import can_manage_declarations
from apps.evacuation.permissions import can_manage_evacuations

register = template.Library()


@register.filter
def is_schedule_manager(user):
    return can_manage_schedules(user)


@register.filter
def is_operations_staff(user):
    return can_manage_sd_records(user)


@register.filter
def is_ebooking_staff(user):
    return can_manage_bookings(user)


@register.filter
def is_declaration_staff(user):
    return can_manage_declarations(user)


@register.filter
def is_evacuation_staff(user):
    return can_manage_evacuations(user)


@register.filter
def is_supervisor(user):
    return is_terminal_supervisor(user)


@register.filter
def has_assigned_sds(user):
    """
    Check if user has any SDs assigned to them.
    Used to conditionally show "Assigned SDs" link in navigation.
    Checks both SD records and schedule entries.
    """
    if not user or not user.is_authenticated:
        return False

    from apps.operations.models import SDRecord, ScheduleEntry

    # Check if user has SDs assigned in SD records
    has_sd_records = SDRecord.objects.filter(officer_assigned=user).exists()
    if has_sd_records:
        return True

    # Check if user has SDs assigned in schedule entries
    has_schedule_entries = ScheduleEntry.objects.filter(assigned_officer=user).exists()
    return has_schedule_entries


@register.filter
def clean_decimal(value):
    """
    Remove trailing zeros from decimal numbers.
    Examples: 50.0000 -> 50, 50.5000 -> 50.5, 50.25 -> 50.25
    """
    if value is None or value == '':
        return ''
    try:
        # Convert to Decimal for precise handling
        if isinstance(value, str):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            value = Decimal(str(value))

        # Convert to string with fixed-point notation (no scientific notation)
        # Use a large number of decimal places, then strip trailing zeros
        str_value = format(value, 'f')

        # If there's a decimal point, remove trailing zeros
        if '.' in str_value:
            str_value = str_value.rstrip('0').rstrip('.')

        return str_value
    except (ValueError, TypeError, ArithmeticError):
        return value
