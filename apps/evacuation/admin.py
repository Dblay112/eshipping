from django.contrib import admin
from .models import Evacuation, EvacuationLine


class EvacuationLineInline(admin.TabularInline):
    """
    Inline admin for evacuation lines within evacuation record.

    Features:
    - Tabular display for compact editing
    - Shows SD number, vessel, agent, container file
    - One extra blank row for adding new lines

    Usage:
        Embedded in EvacuationAdmin for multi-line editing
    """
    model = EvacuationLine
    extra = 1
    fields = ['sd_number', 'sd_record', 'vessel', 'agent', 'container_file']


@admin.register(Evacuation)
class EvacuationAdmin(admin.ModelAdmin):
    """
    Django admin configuration for Evacuation model.

    Features:
    - List display with date, shift, creator, timestamp
    - Filter by shift type and date
    - Search by date and SD numbers in lines
    - Inline editing of evacuation lines
    - Ordered by date (newest first), then shift

    List Display:
        - date: Evacuation date
        - shift: Day or Night shift
        - created_by: User who created the record
        - created_at: Creation timestamp

    Search Fields:
        - date: Evacuation date
        - lines__sd_number: SD numbers in evacuation lines

    Usage:
        Access via Django admin at /admin/evacuation/evacuation/
    """
    list_display = ['date', 'shift', 'created_by', 'created_at']
    list_filter = ['shift', 'date']
    search_fields = ['date', 'lines__sd_number']
    inlines = [EvacuationLineInline]
    ordering = ['-date', 'shift']


@admin.register(EvacuationLine)
class EvacuationLineAdmin(admin.ModelAdmin):
    """
    Django admin configuration for EvacuationLine model.

    Features:
    - List display with SD number, vessel, agent, parent evacuation
    - Filter by shift type (via parent evacuation)
    - Search by SD number, vessel, agent

    List Display:
        - sd_number: SD number for this line
        - vessel: Vessel name
        - agent: Shipping agent
        - evacuation: Parent evacuation record

    Search Fields:
        - sd_number: SD number
        - vessel: Vessel name
        - agent: Agent name

    Usage:
        Access via Django admin at /admin/evacuation/evacuationline/
    """
    list_display = ['sd_number', 'vessel', 'agent', 'evacuation']
    list_filter = ['evacuation__shift']
    search_fields = ['sd_number', 'vessel', 'agent']
