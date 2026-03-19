from django.contrib import admin
from .models import Schedule, ScheduleEntry, SDRecord, SDAllocation, SDContainer, SDClerk, ContainerListUpload


class ScheduleEntryInline(admin.TabularInline):
    model = ScheduleEntry
    extra = 1


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display  = ('date', 'created_by', 'created_at')
    list_filter   = ('date',)
    search_fields = ('date',)
    inlines       = [ScheduleEntryInline]
    ordering      = ('-date',)


class SDAllocationInline(admin.TabularInline):
    model  = SDAllocation
    extra  = 1
    fields = ('allocation_label', 'contract_number', 'mk_number', 'allocated_tonnage', 'buyer', 'agent')


class SDContainerInline(admin.TabularInline):
    model        = SDContainer
    extra        = 0
    readonly_fields = ('from_tally', 'tally_container_id')
    fields       = ('allocation', 'container_number', 'seal_number', 'bag_count',
                    'loading_date', 'balance_after', 'from_tally')


class SDClerkInline(admin.TabularInline):
    model = SDClerk
    extra = 1


@admin.register(SDRecord)
class SDRecordAdmin(admin.ModelAdmin):
    list_display  = ('sd_number', 'vessel_name', 'buyer', 'tonnage', 'container_count', 'is_complete', 'created_at')
    list_filter   = ('is_complete', 'crop_year')
    search_fields = ('sd_number', 'vessel_name', 'buyer', 'si_ref')
    inlines       = [SDAllocationInline, SDContainerInline, SDClerkInline]
    ordering      = ('-created_at',)

    def container_count(self, obj):
        return obj.container_count
    container_count.short_description = 'Containers'


@admin.register(ContainerListUpload)
class ContainerListUploadAdmin(admin.ModelAdmin):
    list_display = ('sd_record', 'contract_number', 'tonnage', 'uploaded_by', 'uploaded_at')
    search_fields = ('sd_record__sd_number', 'contract_number')
    raw_id_fields = ('sd_record', 'allocation', 'uploaded_by')


@admin.register(SDAllocation)
class SDAllocationAdmin(admin.ModelAdmin):
    list_display  = ('sd_record', 'allocation_label', 'contract_number', 'mk_number', 'allocated_tonnage', 'agent')
    search_fields = ('contract_number', 'mk_number', 'sd_record__sd_number')
    list_filter   = ('sd_record',)


@admin.register(SDContainer)
class SDContainerAdmin(admin.ModelAdmin):
    list_display  = ('container_number', 'seal_number', 'sd_record', 'allocation', 'from_tally', 'loading_date')
    search_fields = ('container_number', 'seal_number', 'sd_record__sd_number')
    list_filter   = ('from_tally',)
    readonly_fields = ('from_tally', 'tally_container_id')
