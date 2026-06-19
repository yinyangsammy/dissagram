from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render

from .forms import ContactForm


def contact(request):
    initial_data = {}

    if request.user.is_authenticated:
        initial_data["name"] = request.user.get_username()

        if request.user.email:
            initial_data["email"] = request.user.email

    if request.method == "POST":
        form = ContactForm(request.POST)

        if form.is_valid():
            contact_message = form.save(commit=False)

            if request.user.is_authenticated:
                contact_message.user = request.user

            contact_message.save()

            subject = (
                f"🔥 Dissagram Contact: "
                f"{contact_message.get_reason_display()} — "
                f"{contact_message.subject}"
            )

            body = (
                "New Dissagram contact message\n\n"
                f"Name: {contact_message.name}\n"
                f"Email: {contact_message.email}\n"
                f"Reason: {contact_message.get_reason_display()}\n"
                f"Subject: {contact_message.subject}\n\n"
                "Message:\n"
                f"{contact_message.message}\n\n"
                f"Logged-in user: {request.user if request.user.is_authenticated else 'Guest'}\n"
            )

            try:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.CONTACT_EMAIL],
                    reply_to=[contact_message.email],
                )

                email.send(fail_silently=False)

                messages.success(
                    request,
                    "🔥 Message fired. The complaint cannon has received your payload.",
                )

            except Exception as error:
                print("CONTACT EMAIL ERROR:", error)

                messages.warning(
                    request,
                    "💀 Your message was saved, but the email cannon misfired. Check email settings.",
                )

            return redirect("contact")

        messages.error(
            request,
            "⚠️ Nearly there — check the form and try again.",
        )

    else:
        form = ContactForm(initial=initial_data)

    return render(request, "contact/contact.html", {"form": form})