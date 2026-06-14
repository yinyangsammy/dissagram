from django.urls import path
from . import views

app_name = "disses"


urlpatterns = [
    path("example/", views.diss_example, name="diss_example"),
    path("", views.my_disses, name="my_disses"),
    path("create/", views.diss_create, name="diss_create"),
    path("<int:pk>/", views.diss_detail, name="diss_detail"),
    path("<int:pk>/edit/", views.diss_edit, name="diss_edit"),
    path("<int:pk>/delete/", views.diss_delete, name="diss_delete"),
    path("<int:pk>/deploy/", views.deploy_burn, name="deploy_burn"),
]