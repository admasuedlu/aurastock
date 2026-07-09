from django.contrib.auth.password_validation import validate_password
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.viewsets import CompanyScopedViewSet

from .models import Role, User
from .serializers import (
    ChangePasswordSerializer,
    CompanySignupSerializer,
    RoleSerializer,
    UserSerializer,
)


class CompanySignupView(generics.CreateAPIView):
    """Public self-serve tenant signup: creates the Company, seeds default
    roles, and creates the first (Owner) user."""

    serializer_class = CompanySignupSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": "Incorrect password."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})


class InviteUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "phone",
            "branch", "role", "password",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data, company=self.context["request"].user.company)
        user.set_password(password)
        user.save()
        return user


class UserViewSet(CompanyScopedViewSet):
    queryset = User.objects.select_related("role", "branch").all()
    filterset_fields = ["is_active", "role", "branch"]
    search_fields = ["username", "email", "first_name", "last_name", "phone"]

    def get_serializer_class(self):
        if self.action == "create":
            return InviteUserSerializer
        return UserSerializer


class RoleViewSet(CompanyScopedViewSet):
    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    search_fields = ["name"]
