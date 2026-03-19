from django.urls import path

from .views import (
    allocations_for_sd,
    client_error_report,
    container_list_delete,
    container_list_view,
    daily_port_create,
    daily_port_delete,
    daily_port_edit,
    daily_port_view,
    operations_list,
    schedule_create,
    schedule_delete,
    schedule_edit,
    schedule_view,
    sd_create,
    sd_detail,
    sd_details_json,
    sd_edit,
    sd_export_excel,
    sd_record_delete,
    sd_search_json,
    terminal_schedule_create,
    terminal_schedule_delete,
    terminal_schedule_edit,
    terminal_schedule_list,
    work_program_create,
    work_program_delete,
    work_program_edit,
    work_program_list,
)

urlpatterns = [
    # Schedule
    path('schedule/', schedule_view, name='schedule_view'),
    path('schedule/create/', schedule_create, name='schedule_create'),
    path('schedule/<int:pk>/edit/', schedule_edit, name='schedule_edit'),
    path('schedule/<int:pk>/delete/', schedule_delete, name='schedule_delete'),

    # Terminal Schedule
    path('schedule/terminal/', terminal_schedule_list, name='terminal_schedule_list'),
    path('schedule/terminal/create/', terminal_schedule_create, name='terminal_schedule_create'),
    path('schedule/terminal/<int:pk>/edit/', terminal_schedule_edit, name='terminal_schedule_edit'),
    path('schedule/terminal/<int:pk>/delete/', terminal_schedule_delete, name='terminal_schedule_delete'),

    # Daily Port
    path('daily-port/', daily_port_view, name='daily_port_view'),
    path('daily-port/create/', daily_port_create, name='daily_port_create'),
    path('daily-port/<int:pk>/edit/', daily_port_edit, name='daily_port_edit'),
    path('daily-port/<int:pk>/delete/', daily_port_delete, name='daily_port_delete'),

    # Work Program
    path('work-program/', work_program_list, name='work_program_list'),
    path('work-program/create/', work_program_create, name='work_program_create'),
    path('work-program/<int:pk>/edit/', work_program_edit, name='work_program_edit'),
    path('work-program/<int:pk>/delete/', work_program_delete, name='work_program_delete'),

    # API Endpoints
    path('api/sd-search/', sd_search_json, name='sd_search_json'),
    path('api/sd-details/', sd_details_json, name='sd_details_json'),
    path('api/client-error/', client_error_report, name='client_error_report'),

    # Operations — SD Records
    path('operations/<int:pk>/allocations/', allocations_for_sd, name='allocations_for_sd'),
    path('operations/', operations_list, name='operations_list'),
    path('operations/create/', sd_create, name='sd_create'),
    path('operations/<int:pk>/', sd_detail, name='sd_detail'),
    path('operations/<int:pk>/edit/', sd_edit, name='sd_edit'),
    path('operations/<int:pk>/delete/', sd_record_delete, name='sd_record_delete'),
    path('operations/<int:pk>/excel/', sd_export_excel, name='sd_export_excel'),

    # Container List uploads
    path('operations/<int:pk>/container-list/', container_list_view, name='container_list_view'),
    path('operations/<int:pk>/container-list/<int:upload_pk>/delete/', container_list_delete, name='container_list_delete'),
]
