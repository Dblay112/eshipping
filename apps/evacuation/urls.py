from django.urls import path
from . import views

urlpatterns = [
    path('evacuation/',                         views.evacuation_list,        name='evacuation_list'),
    path('evacuation/create/',                  views.evacuation_create,      name='evacuation_create'),
    path('evacuation/<int:pk>/',                views.evacuation_detail,      name='evacuation_detail'),
    path('evacuation/<int:pk>/edit/',           views.evacuation_edit,        name='evacuation_edit'),
    path('evacuation/<int:pk>/edit/<int:line_pk>/', views.evacuation_edit,    name='evacuation_line_edit'),
    path('evacuation/line/<int:line_pk>/delete/', views.evacuation_line_delete, name='evacuation_line_delete'),
]
