from rest_framework import serializers

from .models import Account, Expense, ExpenseCategory, JournalEntry, JournalEntryLine


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "code", "name", "account_type", "parent", "is_active"]


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalEntryLine
        fields = ["id", "account", "account_code", "account_name", "debit", "credit", "description"]


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalEntryLineSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = ["id", "number", "entry_date", "reference", "description", "source", "lines", "created_at"]
        read_only_fields = fields


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name"]


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    journal_entry_number = serializers.CharField(source="journal_entry.number", read_only=True, default=None)

    class Meta:
        model = Expense
        fields = [
            "id", "category", "category_name", "amount", "expense_date", "description",
            "payment_method", "journal_entry_number", "created_at",
        ]
        read_only_fields = ["expense_date"]
