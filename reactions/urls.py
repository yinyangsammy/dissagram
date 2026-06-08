from django.urls import path
from . import views

app_name = "reactions"

urlpatterns = [
    path(
        "diss/<int:diss_id>/react/",
        views.add_reaction,
        name="add_reaction"
    ),
    path(
        "diss/<int:diss_id>/rate/",
        views.add_burn_rating,
        name="add_burn_rating"
    ),
    path(
        "<int:pk>/edit/",
        views.reaction_edit,
        name="reaction_edit"
    ),
    path(
        "<int:pk>/delete/",
        views.reaction_delete,
        name="reaction_delete"
    ),
]