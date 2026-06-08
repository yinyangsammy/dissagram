from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("", views.package_list, name="packages"),
    path("checkout/<int:package_id>/", views.checkout, name="checkout"),
    path("success/", views.checkout_success, name="success"),
    path("cancel/", views.checkout_cancel, name="cancel"),
    path("webhook/", views.stripe_webhook, name="webhook"),
    path("order/<int:order_id>/", views.order_detail, name="order_detail"),
    path("order/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("order/<int:order_id>/toggle-cancel/", 
         views.toggle_cancel_order, name="toggle_cancel"),
    path("order/<int:order_id>/delete/", views.delete_order, name="delete_order"),
    path("gift/", views.gift_pack, name="gift"),
    path("cache-checkout-data/", views.cache_checkout_data, name="cache_checkout_data"),
    path("history/", views.order_history, name="history"),
]