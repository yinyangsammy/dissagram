from django.shortcuts import render


def diss_example(request):
    return render(request, "disses/diss_example.html")


def my_disses(request):
    return render(request, "disses/my_disses.html")


def diss_create(request):
    return render(request, "disses/diss_form.html")


def diss_detail(request, pk):
    return render(request, "disses/diss_detail.html")


def diss_edit(request, pk):
    return render(request, "disses/diss_form.html")


def diss_delete(request, pk):
    return render(request, "disses/diss_confirm_delete.html")