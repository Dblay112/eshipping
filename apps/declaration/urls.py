from django.urls import path
from . import views

urlpatterns = [
    path('declarations/',               views.declaration_list,   name='declaration_list'),
    path('declarations/create/',        views.declaration_create, name='declaration_create'),
    path('declarations/<int:pk>/edit/', views.declaration_edit,   name='declaration_edit'),
    path('declarations/<int:pk>/delete/', views.declaration_delete, name='declaration_delete'),
]
