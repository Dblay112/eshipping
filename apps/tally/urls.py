from django.urls import path

from .views import (
    all_approved_tallies,
    approve_recall_request,
    approve_tally,
    bulk,
    export_tally_excel,
    japan,
    loading,
    my_tallies,
    new_tally,
    normal_straight,
    pending_tallies,
    recall_tally,
    reject_recall_request,
    reject_tally,
    request_recall,
    straight_20,
    straight_loading_options,
    submit_tally,
    tally_delete,
    tally_edit,
    tally_excel,
    tally_pdf,
    tally_pdf_download,
    tally_success,
    tally_view,
)

urlpatterns = [
    path('loading/', loading, name='loading'),
    path('loading/bulk/', bulk, name='bulk'),
    path('loading/normal_straight/', normal_straight, name='normal_straight'),
    path('loading/japan/', japan, name='japan'),
    path('loading/straight_20/', straight_20, name='straight_20'),
    path('straight_loading_options/', straight_loading_options, name='straight_loading_options'),
    path('loading/tally_success/', tally_success, name='tally_success'),
    path('my_tallies/', my_tallies, name='my_tallies'),
    path('new_tally/', new_tally, name='new_tally'),

    # Tally detail / export
    path('tallies/<int:pk>/view/', tally_view, name='tally_view'),
    path('tallies/<int:pk>/pdf/', tally_pdf, name='tally_pdf'),
    path('tallies/<int:pk>/pdf-download/', tally_pdf_download, name='tally_pdf_download'),
    path('tallies/<int:pk>/excel_download/', tally_excel, name='tally_excel'),
    path('tallies/<int:tally_id>/excel/', export_tally_excel, name='export_tally_excel'),
    path('tallies/<int:pk>/edit/', tally_edit, name='tally_edit'),
    path('tallies/<int:pk>/delete/', tally_delete, name='tally_delete'),

    # Tally approval workflow
    path('tallies/<int:pk>/submit/', submit_tally, name='submit_tally'),
    path('tallies/<int:pk>/approve/', approve_tally, name='approve_tally'),
    path('tallies/<int:pk>/reject/', reject_tally, name='reject_tally'),
    path('tallies/<int:pk>/recall/', recall_tally, name='recall_tally'),  # Deprecated
    path('tallies/<int:pk>/request-recall/', request_recall, name='request_recall'),
    path('recall-requests/<int:request_id>/approve/', approve_recall_request, name='approve_recall_request'),
    path('recall-requests/<int:request_id>/reject/', reject_recall_request, name='reject_recall_request'),
    path('tallies/pending/', pending_tallies, name='pending_tallies'),
    path('tallies/approved/', all_approved_tallies, name='all_approved_tallies'),
]
