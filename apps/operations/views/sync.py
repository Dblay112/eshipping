import logging

from ..models import SDContainer, ScheduleEntry

logger = logging.getLogger(__name__)


def sync_existing_tallies(sd_record):
    """
    Auto-link orphaned records by SD number when an SD record is created.

    This is the core orphaned record auto-linking system. When operations creates
    an SD record, this function finds all existing records with matching SD number
    and links them automatically.

    Links:
    - Tallies: Links orphaned tallies and syncs their containers to SD record
    - Bookings: Links orphaned booking records
    - Declarations: Links orphaned declaration records
    - Evacuations: Links orphaned evacuation lines
    - Schedule Officer Assignments: Syncs assigned officer from schedule to SD

    Features:
    - Case-insensitive SD number matching
    - Only links orphaned records (sd_record is NULL)
    - Syncs tally containers to SD record for tracking
    - Syncs assigned officer from schedule entries
    - Logs all linking activity for audit trail
    - Returns count of linked records by type

    Implementation Notes:
    - Logic moved from views.py for maintainability
    - Behavior unchanged from original implementation
    - Handles ImportError gracefully if apps not installed
    - Uses update_or_create for container syncing to avoid duplicates

    Args:
        sd_record: SDRecord instance that was just created

    Returns:
        dict: Count of linked records by type
        {
            'tallies': 2,
            'bookings': 1,
            'declarations': 1,
            'evacuations': 3,
            'schedule_officer': 1
        }

    Example:
        >>> sd = SDRecord.objects.create(sd_number='SD100', ...)
        >>> counts = sync_existing_tallies(sd)
        >>> print(counts)
        {'tallies': 2, 'bookings': 1, 'declarations': 0, 'evacuations': 1, 'schedule_officer': 1}
    """
    linked_count = {'tallies': 0, 'bookings': 0, 'declarations': 0, 'evacuations': 0, 'schedule_officer': 0}

    # 1. Link Tallies
    try:
        from apps.tally.models import TallyInfo
        tallies = TallyInfo.objects.filter(
            sd_number__iexact=sd_record.sd_number,
            sd_record__isnull=True  # Only link orphaned tallies
        )
        for tally in tallies:
            tally.sd_record = sd_record
            tally.save(update_fields=['sd_record'])
            linked_count['tallies'] += 1

            # Also sync tally containers to SD record
            for tc in tally.containers.all():
                SDContainer.objects.update_or_create(
                    sd_record=sd_record,
                    tally_container_id=tc.pk,
                    defaults={
                        'container_number': tc.container_number or '',
                        'seal_number': tc.seal_number or '',
                        'bag_count': tc.bags or 0,
                        'loading_date': tally.loading_date,
                        'from_tally': True,
                    }
                )
    except ImportError:
        pass  # tally app not installed

    # 2. Link Bookings
    try:
        from apps.ebooking.models import BookingRecord
        bookings = BookingRecord.objects.filter(
            sd_number__iexact=sd_record.sd_number,
            sd_record__isnull=True  # Only link orphaned bookings
        )
        for booking in bookings:
            booking.sd_record = sd_record
            booking.save(update_fields=['sd_record'])
            linked_count['bookings'] += 1
    except ImportError:
        pass

    # 3. Link Declarations
    try:
        from apps.declaration.models import Declaration
        declarations = Declaration.objects.filter(
            sd_number__iexact=sd_record.sd_number,
            sd_record__isnull=True  # Only link orphaned declarations
        )
        for declaration in declarations:
            declaration.sd_record = sd_record
            declaration.save(update_fields=['sd_record'])
            linked_count['declarations'] += 1
    except ImportError:
        pass

    # 4. Link Evacuations
    try:
        from apps.evacuation.models import EvacuationLine
        evac_lines = EvacuationLine.objects.filter(
            sd_number__iexact=sd_record.sd_number,
            sd_record__isnull=True  # Only link orphaned evacuation lines
        )
        for evac_line in evac_lines:
            evac_line.sd_record = sd_record
            evac_line.save(update_fields=['sd_record'])
            linked_count['evacuations'] += 1
    except ImportError:
        pass

    # 5. Sync Schedule Officer Assignment
    try:
        schedule_entry = ScheduleEntry.objects.filter(
            sd_number__iexact=sd_record.sd_number
        ).select_related('assigned_officer').first()

        if schedule_entry and schedule_entry.assigned_officer:
            # Sync officer from schedule to SD record
            if not sd_record.officer_assigned:
                sd_record.officer_assigned = schedule_entry.assigned_officer
                sd_record.save(update_fields=['officer_assigned'])
                linked_count['schedule_officer'] += 1
                logger.info(
                    f'Synced officer {schedule_entry.assigned_officer} from schedule to SD {sd_record.sd_number}'
                )
    except Exception as e:
        logger.warning(f'Could not sync schedule officer for SD {sd_record.sd_number}: {e}')

    # Log what was linked
    total_linked = sum(linked_count.values())
    if total_linked > 0:
        logger.info(
            f'Auto-linked {total_linked} orphaned records to SD {sd_record.sd_number}: '
            f'{linked_count["tallies"]} tallies, {linked_count["bookings"]} bookings, '
            f'{linked_count["declarations"]} declarations, {linked_count["evacuations"]} evacuations, '
            f'{linked_count["schedule_officer"]} schedule officer assignments'
        )

    return linked_count
