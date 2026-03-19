from django.contrib import admin
from .models import TallyInfo, TallyContainer


class TallyContainerInline(admin.TabularInline):
    model = TallyContainer
    extra = 0


@admin.register(TallyInfo)
class TallyInfoAdmin(admin.ModelAdmin):
    list_display = ("tally_number", "sd_number", "mk_number",
                    "first_clerk_name", "date_created")
    ordering = ("-date_created",)
    search_fields = ("tally_number", 'clerk_name', "sd_number",
                     "mk_number", "vessel", "destination")
    inlines = [TallyContainerInline]

    def first_clerk_name(self, obj):
        if isinstance(obj.clerk_name, list) and obj.clerk_name:
            return obj.clerk_name[0]
        return ""
    first_clerk_name.short_description = "Clerk(s)"
