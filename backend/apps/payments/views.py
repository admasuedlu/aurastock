from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PaymentIntent
from .serializers import CreatePaymentIntentSerializer, PaymentIntentSerializer
from .services import confirm_payment_intent, create_payment_intent, handle_webhook


class PaymentIntentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PaymentIntentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["invoice", "status", "provider"]

    def get_queryset(self):
        return PaymentIntent.objects.filter(
            company_id=self.request.user.company_id,
        ).select_related("invoice")

    def create(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            intent = create_payment_intent(
                invoice=data["invoice"], method=data["method"],
                amount=data.get("amount"), user=request.user,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages if hasattr(exc, "messages") else str(exc))
        return Response(PaymentIntentSerializer(intent).data, status=201)

    @action(detail=True, methods=["post"], url_path="simulate-callback")
    def simulate_callback(self, request, pk=None):
        """Sandbox convenience: pretend the provider reported the payer finished
        checkout. In production the provider POSTs the webhook instead -- this
        endpoint just calls the same confirmation path so the sandbox is usable
        without a public callback URL."""
        intent = self.get_object()
        if intent.provider != "sandbox":
            raise DRFValidationError("Only sandbox intents can be simulated; real ones confirm via webhook.")
        try:
            confirm_payment_intent(intent)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages if hasattr(exc, "messages") else str(exc))
        return Response(PaymentIntentSerializer(intent).data)


class PaymentWebhookView(APIView):
    """The public callback a live gateway POSTs to. Unauthenticated by design --
    the provider proves itself with a signature the provider class verifies, not
    a tenant token."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, provider):
        try:
            intent = handle_webhook(provider, request.headers, request.body)
        except DjangoValidationError as exc:
            detail = exc.messages if hasattr(exc, "messages") else str(exc)
            return Response({"detail": detail}, status=400)
        return Response({"reference": intent.reference, "status": intent.status})
