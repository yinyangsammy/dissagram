from django import forms
from django.contrib.auth.models import User

from dissers.models import Disser


class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "profile-input",
            "placeholder": "you@example.com",
        })
    )

    avatar = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "profile-input profile-file-input",
        })
    )

    class Meta:
        model = Disser
        fields = ["avatar"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields["email"].initial = self.user.email

    def save(self, commit=True):
        disser = super().save(commit=False)

        if self.user:
            self.user.email = self.cleaned_data.get("email", "")

            if commit:
                self.user.save()

        if commit:
            disser.save()

        return disser