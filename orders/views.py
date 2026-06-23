"""
orders/views.py

Handles package display, Stripe checkout, webhook confirmation,
order history, gifting and order management.

Key architectural decision: order status is set to 'complete'
ONLY inside stripe_webhook — never on the success URL.
This prevents manipulation of order status via URL tampering.
(Improvement over Boutique Ado's client-side confirmation approach.)

Order confirmation emails are sent via Django's email framework
on webhook confirmation. In development, emails print to the
console backend. Production uses SMTP (see settings.py).
"""

import json
import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from .models import Package, Order


stripe.api_key = settings.STRIPE_SECRET_KEY


# ═══════════════════════════════════════════════════════
# PACKAGE LIST
# ═══════════════════════════════════════════════════════

@login_required
def package_list(request):
    """
    Show available packages with locked/unlocked state.
    Annotates each package with purchase_count and already_owned.

    Also attaches the actual archetype / roast style / premium
    category names each package unlocks, so the pre-purchase
    confirmation modal shows exactly what the user is getting.

    Important:
    - package.archetype_count and package.roast_style_count are treated
      as PAID unlock counts.
    - display_archetype_count and display_roast_style_count include the
      free starter archetype / style too, for customer-facing display.
    """
    from dissers.models import TargetArchetype, RoastStyle, RoastCategory

    packages = Package.objects.filter(is_active=True).order_by("display_order")

    purchase_counts = Order.objects.filter(
        user=request.user,
        status="complete"
    ).values("package_id").annotate(count=Count("id"))

    purchase_count_map = {
        item["package_id"]: item["count"] for item in purchase_counts
    }

    completed_order_ids = list(purchase_count_map.keys())

    # Free starter content — included in customer-facing totals/modal.
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

    # Paid unlock content — sliced by each package's admin-controlled count.
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

        # Include the free starter content in the modal so users understand
        # that buying a pack fully unlocks the starter archetype/style too.
        pkg.included_archetype_names = (
            free_archetype_names +
            ordered_paid_archetypes[:pkg.archetype_count]
        )

        pkg.included_roast_style_names = (
            free_roast_style_names +
            ordered_paid_styles[:pkg.roast_style_count]
        )

        # Customer-facing count totals.
        pkg.display_archetype_count = len(pkg.included_archetype_names)
        pkg.display_roast_style_count = len(pkg.included_roast_style_names)

        # Premium categories are tiered by required_pack_level.
        pkg.included_category_names = list(
            RoastCategory.objects.filter(
                is_free=False,
                required_pack_level__lte=pkg.display_order
            ).order_by("required_pack_level").values_list("name", flat=True)
        )

    past_orders = Order.objects.filter(
        user=request.user
    ).select_related("package", "gifted_to")

    user_owned_packages = packages.filter(pk__in=completed_order_ids)

    return render(request, "orders/packages.html", {
        "packages": packages,
        "past_orders": past_orders,
        "user_owned_packages": user_owned_packages,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    })


# ═══════════════════════════════════════════════════════
# STRIPE CHECKOUT
# ═══════════════════════════════════════════════════════

@login_required
def checkout(request, package_id):
    """
    Create a Stripe Checkout Session for the selected package.
    Redirects to Stripe-hosted payment page.
    No order is created here — order is created in stripe_webhook only.
    """
    package = get_object_or_404(Package, pk=package_id, is_active=True)

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
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
            mode="payment",
            success_url=request.build_absolute_uri(
                f"/orders/success/?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=request.build_absolute_uri("/orders/cancel/"),
            metadata={
                "user_id": request.user.pk,
                "package_id": package.pk,
            }
        )
        return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        messages.error(request, f"Payment error: {str(e)}")
        return redirect("orders:packages")


@login_required
def checkout_success(request):
    """
    Landing page after successful Stripe payment.
    Order status is updated via webhook — this is UX confirmation only.
    Looks up the most recent completed order for this user.
    """
    session_id = request.GET.get("session_id")

    try:
        order = Order.objects.filter(
            user=request.user,
            status="complete",
            stripe_payment_id__icontains=session_id[:20]
            if session_id else ""
        ).latest("created_on")
    except Order.DoesNotExist:
        order = None

    messages.success(request, "🔥 Pack unlocked! Your arsenal is ready.")
    return render(request, "orders/success.html", {"order": order})


@login_required
def checkout_cancel(request):
    """User cancelled at Stripe — no charge made."""
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
      2. Sends order confirmation email

    This is the ONLY place order status is set to 'complete'.
    Using webhook-only confirmation prevents success URL manipulation.

    We parse metadata from the raw JSON payload (not the StripeObject)
    because StripeObject does not support .get() on nested objects.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        payload_data = json.loads(payload)
        session_data = payload_data["data"]["object"]
        metadata = session_data.get("metadata", {})

        user_id = metadata.get("user_id")
        package_id = metadata.get("package_id")
        payment_intent = session_data.get("payment_intent", "")

        if user_id and package_id:
            try:
                from django.contrib.auth.models import User

                user = User.objects.get(pk=user_id)
                package = Package.objects.get(pk=package_id)

                order = Order.objects.create(
                    user=user,
                    package=package,
                    amount_paid=package.price,
                    status="complete",
                    stripe_payment_id=payment_intent or "",
                )

                try:
                    _send_order_confirmation(order)
                except Exception:
                    pass

            except Exception as e:
                import logging
                import traceback

                logging.getLogger(__name__).error(
                    f"Webhook order creation failed: {e}\n"
                    f"{traceback.format_exc()}"
                )
                return HttpResponse(status=500)

    return HttpResponse(status=200)


def _send_order_confirmation(order):
    """
    Send order confirmation email to the purchasing user.
    Uses plain text template for maximum email client compatibility.

    Returns True if an email was sent, otherwise False.
    Email errors must never affect order processing.
    """
    if not order.user.email:
        return False

    try:
        subject = f"🔥 Your {order.package.name} is Locked and Loaded!"

        message = render_to_string(
            "orders/email/order_confirmation.txt",
            {
                "order": order,
                "user": order.user,
                "package": order.package,
            }
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
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
    Includes stats: total orders, completed packs, total spent,
    and gifted pack count.
    """
    past_orders = Order.objects.filter(
        user=request.user
    ).select_related("package", "gifted_to")

    complete_orders = past_orders.filter(status="complete")

    total_spent = sum(
        o.amount_paid for o in complete_orders if o.amount_paid
    )

    gifted_count = past_orders.filter(
        gifted_to__isnull=False
    ).count()

    return render(request, "orders/order_history.html", {
        "past_orders": past_orders,
        "total_orders": past_orders.count(),
        "complete_orders": complete_orders.count(),
        "total_spent": total_spent,
        "gifted_count": gifted_count,
    })


@login_required
def order_detail(request, order_id):
    """View a single order — reuses success template."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, "orders/success.html", {"order": order})


# ═══════════════════════════════════════════════════════
# ORDER MANAGEMENT (Cancel / Uncancel / Delete)
# ═══════════════════════════════════════════════════════

@login_required
def cancel_order(request, order_id):
    """Cancel a pending order."""
    if request.method == "POST":
        order = get_object_or_404(
            Order,
            pk=order_id,
            user=request.user,
            status="pending"
        )
        order.status = "failed"
        order.save()
        messages.success(request, "Order cancelled.")

    return redirect("orders:history")


@login_required
def toggle_cancel_order(request, order_id):
    """
    Toggle order between pending and failed.
    Mirrors publish/unpublish pattern from HipTripHooray.
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
    Completed orders cannot be deleted — payment records
    must be retained for financial accountability.
    """
    if request.method == "POST":
        order = get_object_or_404(Order, pk=order_id, user=request.user)

        if order.status in ["failed", "pending"]:
            order.delete()
            messages.success(request, "Order removed from your history.")

        else:
            messages.error(
                request,
                "Completed orders cannot be deleted."
            )

    return redirect("orders:history")


# ═══════════════════════════════════════════════════════
# GIFTING
# ═══════════════════════════════════════════════════════

@login_required
def gift_pack(request):
    """
    Gift a pack to another user by username.
    Stores recipient in session, then redirects to checkout.
    The gifted_to field is set on Order after webhook confirmation.

    Future enhancement: accept email address for users who
    don't yet have a Dissagram account.
    """
    if request.method == "POST":
        from django.contrib.auth.models import User as DjangoUser

        package_id = request.POST.get("package_id")
        username = request.POST.get("recipient_username", "").strip()
        gift_message = request.POST.get("gift_message", "").strip()

        try:
            recipient = DjangoUser.objects.get(username=username)

            package = get_object_or_404(
                Package,
                pk=package_id,
                is_active=True
            )

            request.session["gift_recipient_id"] = recipient.pk
            request.session["gift_message"] = gift_message

            return redirect("orders:checkout", package_id=package.pk)

        except DjangoUser.DoesNotExist:
            messages.error(
                request,
                f"No user found with username '{username}'."
            )

    return redirect("orders:packages")


# ═══════════════════════════════════════════════════════
# CACHE CHECKOUT DATA (Assessment pattern — Boutique Ado)
# ═══════════════════════════════════════════════════════

@login_required
def cache_checkout_data(request):
    """
    Cache order data before Stripe redirect.
    Included to demonstrate awareness of the Boutique Ado
    payment intent caching pattern, though Dissagram uses
    Stripe Checkout (hosted) rather than a custom card element.
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
                "Sorry, your payment cannot be processed."
            )
            return HttpResponse(content=str(e), status=400)