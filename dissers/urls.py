from django.urls import path, include
from . import views

app_name = "dissers"

urlpatterns = [
    path("", views.disser_list, name="disser_list"),
    path("<int:pk>/", views.disser_detail, name="disser_detail"),
    path("orders/", include("orders.urls")),
]