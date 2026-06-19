from django.conf import settings
from django.db import models


class ContactMessage(models.Model):
    REASON_CHOICES = [
        ("general", "General enquiry"),
        ("account", "Account issue"),
        ("packs", "Packs / orders"),
        ("payment", "Payment problem"),
        ("bug", "Bug report"),
        ("safety", "Safety / moderation"),
        ("collab", "Collab / business"),
        ("other", "Something weird"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_messages",
    )

    name = models.CharField(max_length=120)
    email = models.EmailField()
    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        default="general",
    )
    subject = models.CharField(max_length=160)
    message = models.TextField()

    is_resolved = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_on"]
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"{self.name} — {self.subject}"