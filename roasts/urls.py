from django.urls import path
from . import views

app_name = "roasts"

urlpatterns = [
    path("", views.roast_feed, name="roast_feed"),
    path("my-roasts/", views.my_roasts, name="my_roasts"),
    path("<slug:slug>/", views.roast_detail, name="roast_detail"),
]