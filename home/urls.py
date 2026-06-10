from django.urls import path
from . import views

app_name = "home"


urlpatterns = [
    path("", views.home, name="home"),          # was "home/"
    path("how-it-works/", views.how_it_works, name="how_it_works"),
]