from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name = "expenses"),
    path('add-expense', views.add_expense, name = "add-expenses")
]