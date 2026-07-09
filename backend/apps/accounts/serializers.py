from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Company, SubscriptionPlan

from .models import Permission, Role, User
from .services import seed_default_roles


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "module", "description"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_codes = serializers.SlugRelatedField(
        source="permissions", slug_field="code", many=True,
        queryset=Permission.objects.all(), write_only=True, required=False,
    )

    class Meta:
        model = Role
        fields = ["id", "name", "is_system", "permissions", "permission_codes"]
        read_only_fields = ["is_system"]


class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "phone",
            "company", "branch", "role", "role_name", "is_company_owner",
            "preferred_language", "avatar", "is_active", "date_joined",
        ]
        read_only_fields = ["company", "is_company_owner", "date_joined"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class CompanySignupSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    owner_first_name = serializers.CharField(max_length=150)
    owner_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    owner_email = serializers.EmailField()
    owner_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_owner_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        base_slug = slugify(validated_data["company_name"])
        slug = base_slug
        suffix = 1
        while Company.objects.filter(slug=slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        trial_plan, _ = SubscriptionPlan.objects.get_or_create(
            code="trial",
            defaults={"name": "Free Trial", "price_monthly_etb": 0, "max_users": 5,
                      "max_branches": 1, "max_warehouses": 1},
        )

        company = Company.objects.create(
            name=validated_data["company_name"], slug=slug, subscription_plan=trial_plan,
        )
        roles = seed_default_roles(company)

        user = User.objects.create_user(
            username=f"{slug}-owner",
            email=validated_data["owner_email"],
            password=validated_data["password"],
            first_name=validated_data["owner_first_name"],
            last_name=validated_data.get("owner_last_name", ""),
            phone=validated_data.get("owner_phone", ""),
            company=company,
            role=roles["Owner"],
            is_company_owner=True,
        )
        return {"company": company, "user": user}

    def to_representation(self, instance):
        user = instance["user"]
        refresh = RefreshToken.for_user(user)
        return {
            "company": {"id": str(instance["company"].id), "name": instance["company"].name,
                        "slug": instance["company"].slug},
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
