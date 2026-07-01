"""
orders/views.py

Handles package display, Stripe checkout, webhook confirmation,
order history, gifting and order management.

Key architectural decision: order status is set to 'complete'
ONLY inside stripe_webhook — never on the success URL.
This prevents manipulation of order status via URL tampering.

Order confirmation emails are sent via Django's email framework
on webhook confirmation. In development, emails print to the
console backend. Production uses SMTP (see settings.py).
"""

import json
import logging
import traceback

import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from .models import Order, Package


stripe.api_key = settings.STRIPE_SECRET_KEY


# ═══════════════════════════════════════════════════════
# PACKAGE LIST
# ═══════════════════════════════════════════════════════

@login_required
def package_list(request):
    """
    Show available packages with locked/unlocked state.

    A package counts as owned when:
    - the user bought it for themselves
    - another user bought it as a gift for them

    Packs bought as gifts for somebody else do not count as owned
    by the purchaser.
    """
    from dissers.models import RoastCategory, RoastStyle, TargetArchetype

    packages = list(
        Package.objects.filter(is_active=True).order_by("display_order")
    )

    owned_order_filter = (
        Q(user=request.user, gifted_to__isnull=True) |
        Q(gifted_to=request.user)
    )

    purchase_counts = (
        Order.objects
        .filter(status="complete")
        .filter(owned_order_filter)
        .exclude(package__isnull=True)
        .values("package_id")
        .annotate(count=Count("id"))
    )

    purchase_count_map = {
        item["package_id"]: item["count"] for item in purchase_counts
    }

    owned_package_ids = list(purchase_count_map.keys())

    free_archetype_names = list(
        TargetArchetype.objects.filter(is_free=True)
        .order_by("unlock_priority")
        .values_list("name", flat=True)
    )

    free_roast_style_names = list(
        RoastStyle.objects.filter(is_free=True)
        .order_by("unlock_priority")
        .values_list("name", flat=True)
    )

    ordered_paid_archetypes = list(
        TargetArchetype.objects.filter(is_free=False)
        .order_by("unlock_priority")
        .values_list("name", flat=True)
    )

    ordered_paid_styles = list(
        RoastStyle.objects.filter(is_free=False)
        .order_by("unlock_priority")
        .values_list("name", flat=True)
    )

    for pkg in packages:
        pkg.purchase_count = purchase_count_map.get(pkg.pk, 0)
        pkg.already_owned = pkg.purchase_count > 0

        pkg.included_archetype_names = (
            free_archetype_names +
            ordered_paid_archetypes[:pkg.archetype_count]
        )

        pkg.included_roast_style_names = (
            free_roast_style_names +
            ordered_paid_styles[:pkg.roast_style_count]
        )

        pkg.display_archetype_count = len(pkg.included_archetype_names)
        pkg.display_roast_style_count = len(pkg.included_roast_style_names)

        pkg.included_category_names = list(
            RoastCategory.objects.filter(
                is_free=False,
                required_pack_level__lte=pkg.display_order,
            )
            .order_by("required_pack_level")
            .values_list("name", flat=True)
        )

    user_owned_packages = [
        pkg for pkg in packages if pkg.pk in owned_package_ids
    ]

    past_orders = (
        Order.objects
        .filter(user=request.user)
        .select_related("package", "gifted_to")
        .order_by("-created_on")
    )

    received_gift_orders = (
        Order.objects
        .filter(gifted_to=request.user, status="complete")
        .select_related("package", "user")
        .order_by("-created_on")
    )

    seen_gift_ids = request.session.get("seen_gift_order_ids", [])

    new_gift_orders = received_gift_orders.exclude(pk__in=seen_gift_ids)

    if new_gift_orders.exists():
        latest_gift = new_gift_orders.first()

        messages.success(
            request,
            f"🎁 {latest_gift.user.username} gifted you "
            f"{latest_gift.package.name}! Your arsenal has been upgraded."
        )

        request.session["seen_gift_order_ids"] = (
            seen_gift_ids +
            list(new_gift_orders.values_list("pk", flat=True))
        )
        request.session.modified = True

    return render(request, "orders/packages.html", {
        "packages": packages,
        "past_orders": past_orders,
        "user_owned_packages": user_owned_packages,
        "received_gift_orders": received_gift_orders,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    })


# ═══════════════════════════════════════════════════════
# STRIPE CHECKOUT
# ═══════════════════════════════════════════════════════

@login_required
def checkout(request, package_id):
    """
    Create a Stripe Checkout Session for the selected package.

    No order is created here.
    The order is only created after Stripe confirms payment
    through stripe_webhook.
    """
    package = get_object_or_404(Package, pk=package_id, is_active=True)

    gift_recipient_id = request.session.get("gift_recipient_id", "")
    gift_message = request.session.get("gift_message", "")

    gift_metadata = {
        "user_id": str(request.user.pk),
        "package_id": str(package.pk),
        "gift_recipient_id": str(gift_recipient_id or ""),
        "gift_message": str(gift_message or "")[:200],
    }

    try:
        success_url = (
            request.build_absolute_uri("/orders/success/")
            + "?session_id={CHECKOUT_SESSION_ID}"
        )

        checkout_session_data = {
            "payment_method_types": ["card"],
            "line_items": [{
                "price_data": {
                    "currency": "gbp",
                    "unit_amount": int(package.price * 100),
                    "product_data": {
                        "name": package.name,
                        "description": package.tagline,
                    },
                },
                "quantity": 1,
            }],
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": request.build_absolute_uri("/orders/cancel/"),
            "metadata": gift_metadata,
            "payment_intent_data": {
                "metadata": gift_metadata,
            },
        }

        if request.user.email:
            checkout_session_data["customer_email"] = request.user.email

        checkout_session = stripe.checkout.Session.create(
            **checkout_session_data
        )

        request.session.pop("gift_recipient_id", None)
        request.session.pop("gift_message", None)

        return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        messages.error(request, f"Payment error: {str(e)}")
        return redirect("orders:packages")


@login_required
def checkout_success(request):
    """
    Landing page after successful Stripe payment.

    Order status is updated via webhook — this is UX confirmation only.
    """
    order = (
        Order.objects
        .filter(user=request.user, status="complete")
        .select_related("package", "gifted_to")
        .order_by("-created_on")
        .first()
    )

    if order and order.gifted_to:
        messages.success(
            request,
            f"🎁 Gift sent to {order.gifted_to.username}! "
            "Their arsenal has been upgraded."
        )
    else:
        messages.success(
            request,
            "🔥 Pack unlocked! Your arsenal is ready."
        )

    return render(request, "orders/success.html", {"order": order})


@login_required
def checkout_cancel(request):
    """User cancelled at Stripe — no charge made."""
    request.session.pop("gift_recipient_id", None)
    request.session.pop("gift_message", None)

    messages.info(request, "Payment cancelled — no charge made.")
    return redirect("orders:packages")


# ═══════════════════════════════════════════════════════
# STRIPE WEBHOOK
# ═══════════════════════════════════════════════════════

@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook endpoint.

    Listens for checkout.session.completed and:
    1. Creates the Order record
    2. Saves gifted_to / gift_message when present
    3. Sends order confirmation email

    This is the only place order status is set to 'complete'.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    try:
        payload_data = json.loads(payload)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event_type = payload_data.get("type")

    if event_type != "checkout.session.completed":
        return HttpResponse(status=200)

    session_data = payload_data.get("data", {}).get("object", {})
    metadata = session_data.get("metadata") or {}

    user_id = metadata.get("user_id")
    package_id = metadata.get("package_id")
    gift_recipient_id = metadata.get("gift_recipient_id")
    gift_message = metadata.get("gift_message", "")

    session_id = session_data.get("id", "")
    payment_intent = session_data.get("payment_intent", "")

    customer_details = session_data.get("customer_details") or {}
    checkout_email = (
        customer_details.get("email")
        or session_data.get("customer_email")
        or ""
    )

    payment_reference = payment_intent or session_id

    if not user_id or not package_id or not payment_reference:
        return HttpResponse(status=200)

    try:
        user = User.objects.get(pk=user_id)
        package = Package.objects.get(pk=package_id)

        gifted_to = None

        if gift_recipient_id:
            try:
                gifted_to = User.objects.get(pk=gift_recipient_id)
            except User.DoesNotExist:
                gifted_to = None

        order = Order.objects.filter(
            stripe_payment_id=payment_reference
        ).first()

        created = False

        if order is None:
            order = Order.objects.create(
                user=user,
                package=package,
                amount_paid=package.price,
                status="complete",
                stripe_payment_id=payment_reference,
                gifted_to=gifted_to,
                gift_message=str(gift_message or "")[:200],
            )
            created = True

        if created:
            try:
                _send_order_confirmation(
                    order,
                    fallback_email=checkout_email,
                )
            except Exception:
                pass

    except Exception as e:
        logging.getLogger(__name__).error(
            f"Webhook order creation failed: {e}\n"
            f"{traceback.format_exc()}"
        )
        return HttpResponse(status=500)

    return HttpResponse(status=200)


def _send_order_confirmation(order, fallback_email=None):
    """
    Send order confirmation email to the purchasing user.

    Uses the user's account email first, then falls back to the email
    entered during Stripe Checkout.

    Returns True if an email was sent, otherwise False.
    Email errors must never affect order processing.
    """
    recipient_email = (
        order.user.email
        or fallback_email
        or ""
    ).strip()

    if not recipient_email:
        return False

    try:
        subject = f"🔥 Your {order.package.name} is Locked and Loaded!"

        message = render_to_string(
            "orders/email/order_confirmation.txt",
            {
                "order": order,
                "user": order.user,
                "package": order.package,
            },
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=True,
        )

        return True

    except Exception:
        return False


# ═══════════════════════════════════════════════════════
# ORDER HISTORY
# ═══════════════════════════════════════════════════════

@login_required
def order_history(request):
    """
    Full order history for the logged-in user.

    Shows:
    - packs the user purchased
    - packs gifted to the user
    - packs the user gifted to somebody else
    """
    past_orders = (
        Order.objects
        .filter(
            Q(user=request.user) | Q(gifted_to=request.user)
        )
        .select_related("package", "gifted_to", "user")
        .distinct()
        .order_by("-created_on")
    )

    purchased_orders = past_orders.filter(user=request.user)
    complete_purchased_orders = purchased_orders.filter(status="complete")

    owned_complete_orders = past_orders.filter(
        status="complete"
    ).filter(
        Q(user=request.user, gifted_to__isnull=True) |
        Q(gifted_to=request.user)
    )

    total_spent = sum(
        o.amount_paid
        for o in complete_purchased_orders
        if o.amount_paid
    )

    gifted_count = purchased_orders.filter(
        gifted_to__isnull=False,
        status="complete",
    ).count()

    received_gift_count = past_orders.filter(
        gifted_to=request.user,
        status="complete",
    ).exclude(user=request.user).count()

    return render(request, "orders/order_history.html", {
        "past_orders": past_orders,
        "total_orders": past_orders.count(),
        "complete_orders": owned_complete_orders.count(),
        "total_spent": total_spent,
        "gifted_count": gifted_count,
        "received_gift_count": received_gift_count,
    })


@login_required
def order_detail(request, order_id):
    """View a single order — available to purchaser or gift recipient."""
    order = get_object_or_404(
        Order.objects
        .select_related("package", "gifted_to", "user")
        .filter(
            Q(user=request.user) | Q(gifted_to=request.user)
        ),
        pk=order_id,
    )

    return render(request, "orders/success.html", {"order": order})


# ═══════════════════════════════════════════════════════
# ORDER MANAGEMENT
# ═══════════════════════════════════════════════════════

@login_required
def cancel_order(request, order_id):
    """Cancel a pending order."""
    if request.method == "POST":
        order = get_object_or_404(
            Order,
            pk=order_id,
            user=request.user,
            status="pending",
        )
        order.status = "failed"
        order.save()

        messages.success(request, "Order cancelled.")

    return redirect("orders:history")


@login_required
def toggle_cancel_order(request, order_id):
    """
    Toggle order between pending and failed.
    Allows users to reinstate an accidentally cancelled order.
    """
    if request.method == "POST":
        order = get_object_or_404(Order, pk=order_id, user=request.user)

        if order.status == "pending":
            order.status = "failed"
            messages.success(request, "Order cancelled.")

        elif order.status == "failed":
            order.status = "pending"
            messages.success(request, "Order reinstated!")

        order.save()

    return redirect("orders:history")


@login_required
def delete_order(request, order_id):
    """
    Delete a failed or pending order from history.
    Completed orders cannot be deleted.
    """
    if request.method == "POST":
        order = get_object_or_404(Order, pk=order_id, user=request.user)

        if order.status in ["failed", "pending"]:
            order.delete()
            messages.success(request, "Order removed from your history.")

        else:
            messages.error(
                request,
                "Completed orders cannot be deleted.",
            )

    return redirect("orders:history")


# ═══════════════════════════════════════════════════════
# GIFTING
# ═══════════════════════════════════════════════════════

@login_required
def gift_pack(request):
    """
    Gift a pack to another registered user.

    The form accepts either:
    - username
    - email address

    Gift details are stored briefly in the session, then copied into
    Stripe metadata in checkout().
    """
    if request.method == "POST":
        package_id = request.POST.get("package_id")
        recipient_lookup = request.POST.get(
            "recipient_username", ""
        ).strip()
        gift_message = request.POST.get("gift_message", "").strip()

        if not package_id:
            messages.error(request, "Please choose a pack to gift.")
            return redirect("orders:packages")

        if not recipient_lookup:
            messages.error(request, "Please enter a recipient username.")
            return redirect("orders:packages")

        package = get_object_or_404(
            Package,
            pk=package_id,
            is_active=True,
        )

        recipient = (
            User.objects
            .filter(
                Q(username__iexact=recipient_lookup) |
                Q(email__iexact=recipient_lookup)
            )
            .first()
        )

        if recipient is None:
            messages.error(
                request,
                f"No user found with username or email '{recipient_lookup}'.",
            )
            return redirect("orders:packages")

        if recipient == request.user:
            messages.error(
                request,
                "You already have access to your own account, Bad Boy.",
            )
            return redirect("orders:packages")

        request.session["gift_recipient_id"] = recipient.pk
        request.session["gift_message"] = gift_message[:200]
        request.session.modified = True

        return redirect("orders:checkout", package_id=package.pk)

    return redirect("orders:packages")


# ═══════════════════════════════════════════════════════
# CACHE CHECKOUT DATA
# ═══════════════════════════════════════════════════════

@login_required
def cache_checkout_data(request):
    """
    Cache order data before Stripe redirect.

    Included to demonstrate awareness of the Boutique Ado payment
    intent caching pattern, though Dissagram uses Stripe Checkout
    hosted payment rather than a custom card element.
    """
    if request.method == "POST":
        try:
            pid = request.POST.get(
                "client_secret", ""
            ).split("_secret")[0]

            stripe.api_key = settings.STRIPE_SECRET_KEY

            stripe.PaymentIntent.modify(pid, metadata={
                "username": request.user.username,
            })

            return HttpResponse(status=200)

        except Exception as e:
            messages.error(
                request,
                "Sorry, your payment cannot be processed.",
            )
            return HttpResponse(content=str(e), status=400)

    return HttpResponse(status=405)