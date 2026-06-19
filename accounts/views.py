from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from allauth.account.models import EmailAddress

from dissers.models import Disser
from .forms import ProfileUpdateForm


@login_required
def profile(request):
    disser, _ = Disser.objects.get_or_create(user=request.user)

    return render(
        request,
        "accounts/profile.html",
        {
            "disser": disser,
        }
    )


@login_required
def profile_edit(request):
    disser, _ = Disser.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=disser,
            user=request.user,
        )

        if form.is_valid():
            form.save()

            email = request.user.email.strip() if request.user.email else ""

            if email:
                EmailAddress.objects.filter(user=request.user).update(
                    primary=False
                )

                EmailAddress.objects.update_or_create(
                    user=request.user,
                    email=email,
                    defaults={
                        "primary": True,
                        "verified": True,
                    }
                )

            messages.success(
                request,
                "🔥 Profile updated. Your arena identity has been refreshed.",
            )
            return redirect("accounts:profile")

        messages.error(
            request,
            "⚠️ Nearly there — check the form and try again.",
        )

    else:
        form = ProfileUpdateForm(
            instance=disser,
            user=request.user,
        )

    return render(
        request,
        "accounts/profile_edit.html",
        {
            "form": form,
            "disser": disser,
        }
    )