from django.shortcuts import render


def home(request):
    return render(request, "home/index.html")


def how_it_works(request):
    return render(request, "home/how_it_works.html")