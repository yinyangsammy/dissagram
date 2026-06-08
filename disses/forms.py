from django import forms
from .models import Diss, DissLine


class DissForm(forms.ModelForm):
    """
    Form for creating / editing a Diss.
    The archetype carousel and roast-style dropdown are rendered
    by the template; this form handles validation and the M2M save.
    """

    class Meta:
        model = Diss
        fields = [
            "target_archetype",
            "roast_style",
            "selected_lines",
            "custom_note",
            "status",
            "is_public",
        ]
        widgets = {
            "target_archetype": forms.HiddenInput(),
            "roast_style": forms.HiddenInput(),
            "custom_note": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": (
                    "e.g. This one's for the guy who brings "
                    "a Huel to stand-ups and calls it 'clean living'..."
                ),
                "class": "diss-note",
            }),
            "status": forms.HiddenInput(),
            "is_public": forms.HiddenInput(),
        }

    def __init__(self, *args, archetype=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope selected_lines to the chosen archetype so the
        # queryset is tight and validation rejects rogue POSTs.
        if archetype:
            self.fields["selected_lines"].queryset = (
                DissLine.objects.filter(
                    archetype=archetype,
                    status="approved",
                )
            )
        else:
            self.fields["selected_lines"].queryset = DissLine.objects.none()

        self.fields["selected_lines"].required = True
        self.fields["selected_lines"].error_messages = {
            "required": "Pick at least one burn line to fire.",
        }

    def clean(self):
        cleaned = super().clean()
        archetype = cleaned.get("target_archetype")
        roast_style = cleaned.get("roast_style")
        lines = cleaned.get("selected_lines")

        if not archetype:
            self.add_error(None, "Please select a target archetype.")

        if not roast_style:
            self.add_error(None, "Please choose a roast style.")

        if lines:
            # Guard: every line must belong to the selected archetype
            bad = lines.exclude(archetype=archetype)
            if bad.exists():
                self.add_error(
                    "selected_lines",
                    "One or more lines don't belong to that archetype.",
                )

        return cleaned
