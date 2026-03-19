from django.urls import path
from . import views

urlpatterns = [
    path('booking/',              views.booking_list,   name='booking_list'),
    path('booking/assigned/',     views.assigned_sds_list, name='assigned_sds_list'),
    path('booking/create/',       views.booking_create, name='booking_create'),
    path('booking/<int:pk>/edit/', views.booking_edit,  name='booking_edit'),
    path('booking/detail/<int:detail_pk>/delete/', views.booking_detail_delete, name='booking_detail_delete'),

    # API endpoint for booking data
    path('booking/api/data/', views.booking_data_json, name='booking_data_json'),

    # Correction tracking
    path('booking/detail/<int:detail_pk>/correction/add/', views.booking_add_correction, name='booking_add_correction'),
    path('booking/detail/<int:detail_pk>/corrections/', views.booking_correction_history, name='booking_correction_history'),

    # Debug endpoint
    path('booking/debug/', views.debug_model_config, name='debug_model_config'),
]
