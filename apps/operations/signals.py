"""
sd_tracker/signals.py

1. Tally Container Sync: When a TallyInfo (or TallyContainer) is saved,
   automatically create/update SDContainer rows for the matching SDRecord.

2. Backward Linkage: When an SDRecord is created, automatically link all
   existing records from other desks (bookings, declarations, evacuations,
   tallies) with matching SD number. Also picks up assigned officer from schedule.

3. Tally Container Cleanup: When a TallyContainer is deleted, remove the
   corresponding SDContainer record to maintain data integrity.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import MultipleObjectsReturned
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='tally.TallyContainer')
def sync_tally_container_to_sd(sender, instance, created, **kwargs):
    """
    Sync approved tally container data to SD record automatically.

    Fires every time a TallyContainer is saved (created or updated).
    Creates or updates corresponding SDContainer record for the matching SD.

    Workflow:
    1. Get parent TallyInfo's sd_number
    2. Find matching SDRecord (case-insensitive)
    3. Upsert SDContainer with container details
    4. Skip if SD doesn't exist yet (orphaned tally)

    Features:
    - Case-insensitive SD number matching
    - Atomic transaction for data integrity
    - Graceful handling of missing SD records
    - Error logging for debugging

    Args:
        sender: TallyContainer model class
        instance: TallyContainer instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional signal arguments

    Example:
        When clerk saves tally container:
        >>> container.save()
        # Signal fires automatically
        # SDContainer created/updated with container_number, seal_number, bag_count

    Error Handling:
        - SDRecord.DoesNotExist: Silently skip (tally created before SD)
        - MultipleObjectsReturned: Log error (data integrity issue)
        - Exception: Log error and continue (don't block tally save)
    """
    from .models import SDRecord, SDContainer

    tally = instance.tally  # TallyInfo instance
    sd_number = (tally.sd_number or '').strip()
    if not sd_number:
        return  # tally has no SD number — nothing to sync

    # Find the matching SD record (case-insensitive)
    try:
        sd_record = SDRecord.objects.get(sd_number__iexact=sd_number)
    except SDRecord.DoesNotExist:
        return  # no matching SD yet — clerk created tally before ops created SD, skip
    except MultipleObjectsReturned:
        logger.error(f'[TALLY SYNC] Multiple SD records found for {sd_number} - data integrity issue')
        return

    # Upsert: create if not exists, update if already there
    try:
        with transaction.atomic():
            SDContainer.objects.update_or_create(
                sd_record=sd_record,
                tally_container_id=instance.pk,
                defaults={
                    'container_number': instance.container_number or '',
                    'seal_number':      instance.seal_number or '',
                    'bag_count':        instance.bags or 0,
                    'loading_date':     tally.loading_date,
                    'from_tally':       True,
                }
            )
    except Exception as e:
        logger.error(f'[TALLY SYNC] Error syncing container {instance.pk}: {e}')


@receiver(post_save, sender='tally.TallyInfo')
def sync_all_tally_containers_on_tally_save(sender, instance, **kwargs):
    """
    Re-sync all containers when TallyInfo is saved (e.g., SD number corrected).

    Fires when TallyInfo itself is saved, not just containers. Ensures all
    containers are synced to the correct SD record if SD number was changed.

    Use Cases:
    - Clerk corrects SD number on existing tally
    - Tally is edited and SD number updated
    - Ensures no containers are missed in sync

    Workflow:
    1. Get tally's sd_number
    2. Find matching SDRecord (case-insensitive)
    3. Loop through all containers in tally
    4. Upsert SDContainer for each container
    5. Skip if SD doesn't exist yet

    Features:
    - Syncs ALL containers in one transaction
    - Case-insensitive SD number matching
    - Atomic transaction for data integrity
    - Error logging for debugging

    Args:
        sender: TallyInfo model class
        instance: TallyInfo instance being saved
        **kwargs: Additional signal arguments

    Example:
        When clerk updates tally SD number:
        >>> tally.sd_number = 'SD200'
        >>> tally.save()
        # Signal fires automatically
        # All containers re-synced to SD200

    Error Handling:
        - SDRecord.DoesNotExist: Silently skip (tally created before SD)
        - MultipleObjectsReturned: Log error (data integrity issue)
        - Exception: Log error and continue (don't block tally save)
    """
    from .models import SDRecord, SDContainer

    sd_number = (instance.sd_number or '').strip()
    if not sd_number:
        return

    try:
        sd_record = SDRecord.objects.get(sd_number__iexact=sd_number)
    except SDRecord.DoesNotExist:
        return
    except MultipleObjectsReturned:
        logger.error(f'[TALLY SYNC] Multiple SD records found for {sd_number} - data integrity issue')
        return

    try:
        with transaction.atomic():
            for tc in instance.containers.all():
                SDContainer.objects.update_or_create(
                    sd_record=sd_record,
                    tally_container_id=tc.pk,
                    defaults={
                        'container_number': tc.container_number or '',
                        'seal_number':      tc.seal_number or '',
                        'bag_count':        tc.bags or 0,
                        'loading_date':     instance.loading_date,
                        'from_tally':       True,
                    }
                )
    except Exception as e:
        logger.error(f'[TALLY SYNC] Error syncing containers for tally {instance.pk}: {e}')


@receiver(post_save, sender='operations.SDRecord')
def link_existing_records_to_sd(sender, instance, created, **kwargs):
    """
    Auto-link orphaned records when SD is created (backward linkage).

    CRITICAL FEATURE: Enables flexible workflow where desks can create records
    before or after operations creates the SD. Linkage happens automatically.

    Workflow:
    1. Operations desk creates SD record
    2. Signal searches for orphaned records with matching SD number
    3. Links all found records to the new SD
    4. Picks up assigned officer from schedule if available
    5. Logs linkage results for audit trail

    Records Linked:
    - BookingRecord: Ebooking desk bookings
    - Declaration: Declaration desk declarations
    - EvacuationLine: Evacuation desk container movements
    - TallyInfo: Clerk tally records
    - ScheduleEntry: Assigned officer from schedule

    Features:
    - Case-insensitive SD number matching
    - Atomic transaction for data integrity
    - Comprehensive logging for audit trail
    - Only runs for new SD records (not updates)
    - Graceful error handling (doesn't block SD creation)

    Args:
        sender: SDRecord model class
        instance: SDRecord instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional signal arguments

    Example:
        Scenario: Clerk creates tally for SD100 before operations creates SD100
        1. Clerk creates tally with sd_number='SD100' (orphaned)
        2. Operations creates SD100
        3. Signal fires automatically
        4. Tally linked to SD100
        5. Log: "SD SD100 created - automatically linked 1 existing records: Tallies=1"

    Logging:
        - Info: Successful linkage with counts
        - Info: No records to link
        - Error: Linkage failures (doesn't block SD creation)

    Performance Note:
        Runs on every SD creation. Queries multiple tables but uses atomic transaction.
    """
    from .models import SDRecord

    if not created:
        # Only run for new SD records, not updates
        return

    sd_number = instance.sd_number
    linked_count = {
        'bookings': 0,
        'declarations': 0,
        'evacuations': 0,
        'tallies': 0,
        'schedule_officer': False,
    }

    try:
        with transaction.atomic():
            # Link BookingRecords
            from apps.ebooking.models import BookingRecord
            bookings = BookingRecord.objects.filter(
                sd_number__iexact=sd_number,
                sd_record__isnull=True
            )
            count = bookings.update(sd_record=instance)
            linked_count['bookings'] = count

            # Link Declarations
            from apps.declaration.models import Declaration
            declarations = Declaration.objects.filter(
                sd_number__iexact=sd_number,
                sd_record__isnull=True
            )
            count = declarations.update(sd_record=instance)
            linked_count['declarations'] = count

            # Link EvacuationLines
            from apps.evacuation.models import EvacuationLine
            evac_lines = EvacuationLine.objects.filter(
                sd_number__iexact=sd_number,
                sd_record__isnull=True
            )
            count = evac_lines.update(sd_record=instance)
            linked_count['evacuations'] = count

            # Link TallyInfo records
            from apps.tally.models import TallyInfo
            tallies = TallyInfo.objects.filter(
                sd_number__iexact=sd_number,
                sd_record__isnull=True
            )
            count = tallies.update(sd_record=instance)
            linked_count['tallies'] = count

            # Pick up assigned officer from schedule if available
            from apps.operations.models import ScheduleEntry
            try:
                schedule_entry = ScheduleEntry.objects.filter(
                    sd_number__iexact=sd_number,
                    assigned_officer__isnull=False
                ).first()

                if schedule_entry and schedule_entry.assigned_officer:
                    instance.officer_assigned = schedule_entry.assigned_officer
                    instance.save(update_fields=['officer_assigned'])
                    linked_count['schedule_officer'] = True
            except Exception as e:
                logger.error(f'[SD LINKAGE] Error linking officer for SD {sd_number}: {e}')

        # Log the linkage results
        total_linked = sum(v for v in linked_count.values() if isinstance(v, int))
        if total_linked > 0 or linked_count['schedule_officer']:
            logger.info(
                f'[SD LINKAGE] SD {sd_number} created - automatically linked '
                f'{total_linked} existing records: '
                f'Bookings={linked_count["bookings"]}, '
                f'Declarations={linked_count["declarations"]}, '
                f'Evacuations={linked_count["evacuations"]}, '
                f'Tallies={linked_count["tallies"]}, '
                f'Officer={"Yes" if linked_count["schedule_officer"] else "No"}'
            )
        else:
            logger.info(f'[SD LINKAGE] SD {sd_number} created - no existing records to link')

    except Exception as e:
        logger.error(f'[SD LINKAGE] Error linking records for SD {sd_number}: {e}')
        # Don't raise - let the SD creation succeed even if linkage fails


@receiver(pre_delete, sender='tally.TallyContainer')
def cleanup_sd_container_on_tally_container_delete(sender, instance, **kwargs):
    """
    Remove SDContainer when TallyContainer is deleted (data integrity).

    Fires before TallyContainer is deleted. Ensures SD records don't show
    containers from deleted tallies.

    Use Cases:
    - Clerk deletes individual container from tally
    - Tally is edited and containers removed
    - Maintains data integrity between tally and SD

    Features:
    - Removes corresponding SDContainer record
    - Logs deletion for audit trail
    - Error logging for debugging
    - Doesn't block deletion on error

    Args:
        sender: TallyContainer model class
        instance: TallyContainer instance being deleted
        **kwargs: Additional signal arguments

    Example:
        When clerk deletes container:
        >>> container.delete()
        # Signal fires automatically
        # SDContainer removed
        # Log: "Removed SDContainer for TallyContainer 123"

    Error Handling:
        - Exception: Log error and continue (don't block deletion)
    """
    from .models import SDContainer

    try:
        SDContainer.objects.filter(tally_container_id=instance.pk).delete()
        logger.info(f'[TALLY CLEANUP] Removed SDContainer for TallyContainer {instance.pk}')
    except Exception as e:
        logger.error(f'[TALLY CLEANUP] Error removing SDContainer for TallyContainer {instance.pk}: {e}')


@receiver(pre_delete, sender='tally.TallyInfo')
def cleanup_sd_containers_on_tally_delete(sender, instance, **kwargs):
    """
    Remove all SDContainers when TallyInfo is deleted (data integrity).

    Fires before TallyInfo is deleted. Ensures SD records don't show
    containers from deleted tallies.

    Use Cases:
    - Clerk deletes entire tally
    - Supervisor deletes rejected tally
    - Maintains data integrity between tally and SD

    Workflow:
    1. Get all container IDs for this tally
    2. Delete all corresponding SDContainer records
    3. Log deletion count for audit trail

    Features:
    - Removes ALL SDContainer records for tally
    - Logs deletion count for audit trail
    - Error logging for debugging
    - Doesn't block deletion on error

    Args:
        sender: TallyInfo model class
        instance: TallyInfo instance being deleted
        **kwargs: Additional signal arguments

    Example:
        When clerk deletes tally with 10 containers:
        >>> tally.delete()
        # Signal fires automatically
        # All 10 SDContainers removed
        # Log: "Removed 10 SDContainer records for deleted tally TALLY-001"

    Error Handling:
        - Exception: Log error and continue (don't block deletion)
    """
    from .models import SDContainer

    try:
        # Get all container IDs for this tally
        container_ids = list(instance.containers.values_list('pk', flat=True))
        if container_ids:
            deleted_count = SDContainer.objects.filter(tally_container_id__in=container_ids).delete()[0]
            logger.info(f'[TALLY CLEANUP] Removed {deleted_count} SDContainer records for deleted tally {instance.tally_number}')
    except Exception as e:
        logger.error(f'[TALLY CLEANUP] Error removing SDContainers for tally {instance.pk}: {e}')
