"""
Management command to wipe all data from the database.
Use with caution - this deletes everything!

Usage: python manage.py wipe_data --confirm
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tally.models import TallyInfo, TallyContainer, RecallRequest
from apps.operations.models import (
    SDRecord, SDAllocation, SDContainer, SDClerk,
    Schedule, ScheduleEntry, Terminal, WorkProgram, DailyPort
)
from apps.ebooking.models import BookingRecord, BookingLine, BookingDetail, BookingCorrection
from apps.declaration.models import Declaration, DeclarationLine
from apps.evacuation.models import EvacuationRecord, EvacuationLine

Account = get_user_model()


class Command(BaseCommand):
    help = 'Wipe all data from the database (use with caution!)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all data',
        )
        parser.add_argument(
            '--keep-users',
            action='store_true',
            help='Keep user accounts (only delete operational data)',
        )

    def handle(self, *args, **options):
        # ============================================================================
        # COMMAND TEMPORARILY DISABLED FOR PRODUCTION
        # This command is commented out to prevent accidental data deletion
        # To re-enable: uncomment the code block below
        # ============================================================================

        self.stdout.write(
            self.style.ERROR(
                '⚠️  DATA WIPE COMMAND IS CURRENTLY DISABLED\n\n'
                'This command has been temporarily disabled to protect production data.\n'
                'To re-enable this command, edit the file:\n'
                'apps/core/management/commands/wipe_data.py\n\n'
                'Uncomment the deletion code in the handle() method.'
            )
        )
        return

        # ============================================================================
        # DELETION CODE (COMMENTED OUT)
        # ============================================================================

        # if not options['confirm']:
        #     self.stdout.write(
        #         self.style.ERROR(
        #             'This command will DELETE ALL DATA from the database!\n'
        #             'Run with --confirm flag to proceed: python manage.py wipe_data --confirm'
        #         )
        #     )
        #     return

        # self.stdout.write(self.style.WARNING('Starting data wipe...'))

        # deleted_counts = {}

        # # Recall requests
        # count = RecallRequest.objects.all().delete()[0]
        # deleted_counts['Recall Requests'] = count
        # self.stdout.write(f'Deleted {count} recall requests')

        # # Tallies
        # count = TallyContainer.objects.all().delete()[0]
        # deleted_counts['Tally Containers'] = count
        # self.stdout.write(f'Deleted {count} tally containers')

        # count = TallyInfo.objects.all().delete()[0]
        # deleted_counts['Tallies'] = count
        # self.stdout.write(f'Deleted {count} tallies')

        # # Bookings
        # count = BookingCorrection.objects.all().delete()[0]
        # deleted_counts['Booking Corrections'] = count
        # self.stdout.write(f'Deleted {count} booking corrections')

        # count = BookingDetail.objects.all().delete()[0]
        # deleted_counts['Booking Details'] = count
        # self.stdout.write(f'Deleted {count} booking details')

        # count = BookingLine.objects.all().delete()[0]
        # deleted_counts['Booking Lines'] = count
        # self.stdout.write(f'Deleted {count} booking lines')

        # count = BookingRecord.objects.all().delete()[0]
        # deleted_counts['Booking Records'] = count
        # self.stdout.write(f'Deleted {count} booking records')

        # # Declarations
        # count = DeclarationLine.objects.all().delete()[0]
        # deleted_counts['Declaration Lines'] = count
        # self.stdout.write(f'Deleted {count} declaration lines')

        # count = Declaration.objects.all().delete()[0]
        # deleted_counts['Declarations'] = count
        # self.stdout.write(f'Deleted {count} declarations')

        # # Evacuations
        # count = EvacuationLine.objects.all().delete()[0]
        # deleted_counts['Evacuation Lines'] = count
        # self.stdout.write(f'Deleted {count} evacuation lines')

        # count = EvacuationRecord.objects.all().delete()[0]
        # deleted_counts['Evacuation Records'] = count
        # self.stdout.write(f'Deleted {count} evacuation records')

        # # SD Records
        # count = SDClerk.objects.all().delete()[0]
        # deleted_counts['SD Clerks'] = count
        # self.stdout.write(f'Deleted {count} SD clerks')

        # count = SDContainer.objects.all().delete()[0]
        # deleted_counts['SD Containers'] = count
        # self.stdout.write(f'Deleted {count} SD containers')

        # count = SDAllocation.objects.all().delete()[0]
        # deleted_counts['SD Allocations'] = count
        # self.stdout.write(f'Deleted {count} SD allocations')

        # count = SDRecord.objects.all().delete()[0]
        # deleted_counts['SD Records'] = count
        # self.stdout.write(f'Deleted {count} SD records')

        # # Schedules
        # count = ScheduleEntry.objects.all().delete()[0]
        # deleted_counts['Schedule Entries'] = count
        # self.stdout.write(f'Deleted {count} schedule entries')

        # count = Schedule.objects.all().delete()[0]
        # deleted_counts['Schedules'] = count
        # self.stdout.write(f'Deleted {count} schedules')

        # # Work Programs and Daily Ports
        # count = WorkProgram.objects.all().delete()[0]
        # deleted_counts['Work Programs'] = count
        # self.stdout.write(f'Deleted {count} work programs')

        # count = DailyPort.objects.all().delete()[0]
        # deleted_counts['Daily Ports'] = count
        # self.stdout.write(f'Deleted {count} daily ports')

        # # Terminals (clear supervisors but keep terminals)
        # for terminal in Terminal.objects.all():
        #     terminal.supervisors.clear()
        # self.stdout.write('Cleared terminal supervisor assignments')

        # # Users (optional)
        # if not options['keep_users']:
        #     Terminal.objects.all().delete()
        #     deleted_counts['Terminals'] = Terminal.objects.count()
        #     self.stdout.write('Deleted all terminals')

        #     count = Account.objects.all().delete()[0]
        #     deleted_counts['User Accounts'] = count
        #     self.stdout.write(f'Deleted {count} user accounts')
        # else:
        #     self.stdout.write(self.style.WARNING('Kept user accounts and terminals'))

        # # Summary
        # self.stdout.write(self.style.SUCCESS('\n=== DATA WIPE COMPLETE ==='))
        # total = sum(deleted_counts.values())
        # self.stdout.write(self.style.SUCCESS(f'Total records deleted: {total}'))

        # if not options['keep_users']:
        #     self.stdout.write(
        #         self.style.WARNING(
        #             '\nAll data including users has been wiped.\n'
        #             'Create a new superuser with: python manage.py createsuperuser'
        #         )
        #     )
        # else:
        #     self.stdout.write(
        #         self.style.SUCCESS(
        #             '\nOperational data wiped. User accounts and terminals preserved.'
        #         )
        #     )
