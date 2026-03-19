from django.contrib import admin
from .models import Declaration


@admin.register(Declaration)
class DeclarationAdmin(admin.ModelAdmin):
    """
    Django admin configuration for Declaration model.

    Features:
    - List display with key declaration information
    - Search by SD number, declaration number, agent, vessel
    - Filter by creation date
    - Raw ID fields for foreign keys (performance optimization)
    - Ordered by creation date (newest first)

    List Display:
        - declaration_number: Customs declaration number
        - sd_number: SD number
        - agent: Shipping agent
        - vessel: Vessel name
        - tonnage: Tonnage declared
        - created_by: User who created the declaration
        - created_at: Creation timestamp

    Search Fields:
        - sd_number: SD number
        - declaration_number: Declaration number
        - agent: Agent name
        - vessel: Vessel name

    Usage:
        Access via Django admin at /admin/declaration/declaration/
    """
    list_display = ['declaration_number', 'sd_number', 'agent', 'vessel', 'tonnage', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['sd_number', 'declaration_number', 'agent', 'vessel']
    raw_id_fields = ['sd_record', 'created_by']
    ordering = ['-created_at']
