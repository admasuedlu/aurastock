from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PaymentIntentViewSet, PaymentWebhookView

router = DefaultRouter()
router.register("payment-intents", PaymentIntentViewSet, basename="payment-intent")

urlpatterns = [
    path("payments/webhook/<str:provider>/", PaymentWebhookView.as_view(), name="payment-webhook"),
    *router.urls,
]
