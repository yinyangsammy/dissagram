import stripe
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import Package, Order

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def checkout(request, package_id):
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
def order_history(request):
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
def checkout_success(request):
    session_id = request.GET.get("session_id")
    try:
        # Find the order created by webhook
        order = Order.objects.filter(
            user=request.user,
            status="complete",
            stripe_payment_id__icontains=session_id[:20]
                if session_id else ""
        ).latest("created_on")
    except Order.DoesNotExist:
        order = None

    messages.success(
        request, "🔥 Pack unlocked! Your arsenal is ready."
    )
    return render(
        request, "orders/success.html", {"order": order}
    )


@login_required
def checkout_cancel(request):
    """User cancelled at Stripe — redirect back to packages."""
    messages.info(request, "Payment cancelled — no charge made.")
    return redirect("orders:packages")


@login_required
def package_list(request):
    """Show available packages with locked/unlocked state."""
    packages = Package.objects.filter(is_active=True)
    completed_order_ids = Order.objects.filter(
        user=request.user,
        status="complete"
    ).values_list("package_id", flat=True)

    for pkg in packages:
        pkg.already_owned = pkg.pk in completed_order_ids

    past_orders = Order.objects.filter(
        user=request.user
    ).select_related("package", "gifted_to")

    # Packages the user owns (for gift form)
    user_owned_packages = packages.filter(
        pk__in=completed_order_ids
    )

    return render(request, "orders/packages.html", {
        "packages": packages,
        "past_orders": past_orders,
        "user_owned_packages": user_owned_packages,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    })


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"].get("user_id")
        package_id = session["metadata"].get("package_id")

        if user_id and package_id:
            try:
                from django.contrib.auth.models import User
                user = User.objects.get(pk=user_id)
                package = Package.objects.get(pk=package_id)

                Order.objects.create(
                    user=user,
                    package=package,
                    amount_paid=package.price,
                    status="complete",
                    stripe_payment_id=session.get(
                        "payment_intent", ""
                    ),
                )
            except (User.DoesNotExist, Package.DoesNotExist):
                pass

    return HttpResponse(status=200)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, "orders/success.html", {"order": order})


@login_required
def cancel_order(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(
            Order, pk=order_id, user=request.user, status="pending"
        )
        order.status = "failed"
        order.save()
        messages.success(request, "Order cancelled.")
    return redirect("orders:history")  # ← was "orders:packages"


@login_required
def toggle_cancel_order(request, order_id):
    """Toggle order between pending and failed — mirrors publish/unpublish pattern."""
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
    if request.method == "POST":
        order = get_object_or_404(
            Order, pk=order_id, user=request.user
        )
        # Only allow deleting failed/cancelled orders
        # Never delete completed orders — payment records must be kept
        if order.status in ["failed", "pending"]:
            order.delete()
            messages.success(request, "Order removed from your history.")
        else:
            messages.error(request, "Completed orders cannot be deleted.")
    return redirect("orders:history")


@login_required
def gift_pack(request):
    if request.method == "POST":
        from django.contrib.auth.models import User as DjangoUser
        package_id = request.POST.get("package_id")
        username = request.POST.get("recipient_username", "").strip()
        gift_message = request.POST.get("gift_message", "").strip()

        try:
            recipient = DjangoUser.objects.get(username=username)
            package = get_object_or_404(Package, pk=package_id, is_active=True)

            # Create a gifted order — goes straight to checkout
            # but tagged with gifted_to
            request.session["gift_recipient_id"] = recipient.pk
            request.session["gift_message"] = gift_message
            return redirect("orders:checkout", package_id=package.pk)

        except DjangoUser.DoesNotExist:
            messages.error(request, f"No user found with username '{username}'.")

    return redirect("orders:packages")


@login_required
def cache_checkout_data(request):
    """Cache order data before Stripe redirect — assessment pattern."""
    if request.method == "POST":
        try:
            pid = request.POST.get("client_secret", "").split("_secret")[0]
            stripe.api_key = settings.STRIPE_SECRET_KEY
            stripe.PaymentIntent.modify(pid, metadata={
                "username": request.user.username,
            })
            return HttpResponse(status=200)
        except Exception as e:
            messages.error(request, "Sorry, your payment cannot be processed.")
            return HttpResponse(content=str(e), status=400)


    