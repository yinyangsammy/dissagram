from django import forms
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    """
    Public contact form for Dissagram.
    Includes a hidden honeypot field to catch basic spam bots.
    """

    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="Leave empty",
    )

    class Meta:
        model = ContactMessage
        fields = [
            "name",
            "email",
            "reason",
            "subject",
            "message",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "contact-input",
                "placeholder": "Your name",
            }),
            "email": forms.EmailInput(attrs={
                "class": "contact-input",
                "placeholder": "you@example.com",
            }),
            "reason": forms.Select(attrs={
                "class": "contact-input contact-select",
            }),
            "subject": forms.TextInput(attrs={
                "class": "contact-input",
                "placeholder": "What needs saying?",
            }),
            "message": forms.Textarea(attrs={
                "class": "contact-input contact-textarea",
                "rows": 7,
                "placeholder": "Tell us what happened. Deploy responsibly...",
            }),
        }

    def clean_honeypot(self):
        honeypot = self.cleaned_data.get("honeypot")

        if honeypot:
            raise forms.ValidationError("Spam detected.")

        return honeypot