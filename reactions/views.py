from django.shortcuts import render


def add_reaction(request, diss_id):
    return render(request, "reactions/add_reaction.html")


def add_burn_rating(request, diss_id):
    return render(request, "reactions/add_burn_rating.html")


def reaction_edit(request, pk):
    return render(request, "reactions/reaction_edit.html")


def reaction_delete(request, pk):
    return render(request, "reactions/reaction_confirm_delete.html")