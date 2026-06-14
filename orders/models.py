from django.db import models
from django.contrib.auth.models import User
from disses.models import Diss


class Package(models.Model):
    """
    Purchasable diss card packs.
    """
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    archetype_count = models.IntegerField(default=2)
    roast_style_count = models.IntegerField(default=2)
    premium_category_count = models.IntegerField(default=1)
    deploy_burn_count = models.IntegerField(default=0)
    riposte_count = models.IntegerField(default=0)
    includes_leaderboard = models.BooleanField(default=False)
    stripe_price_id = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    max_line_selections = models.IntegerField(
        default=3,
        help_text="Max disslines user can select (free=1, Diss=2, Burn=3)"
    )

    class Meta:
        ordering = ["display_order"]
        verbose_name = "Package"
        verbose_name_plural = "Packages"

    def __str__(self):
        return f"{self.name} — £{self.price}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("complete", "Complete"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        null=True
    )
    diss = models.OneToOneField(
        Diss,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="order"
    )
    stripe_payment_id = models.CharField(max_length=200, blank=True)
    amount_paid = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    # Gift fields — on Order, not Package ✅
    gifted_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="gifted_orders",
        help_text="If purchased as a gift for another user"
    )
    gift_message = models.CharField(max_length=200, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_on"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order #{self.pk} — {self.user.username} — {self.status}"
