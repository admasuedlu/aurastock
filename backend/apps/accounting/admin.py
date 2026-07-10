from django.contrib import admin

from .models import Account, Expense, ExpenseCategory, JournalEntry, JournalEntryLine


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "account_type", "company", "is_active"]
    list_filter = ["company", "account_type", "is_active"]


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["number", "company", "entry_date", "source", "reference"]
    list_filter = ["company", "source"]
    inlines = [JournalEntryLineInline]


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "company"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["description", "company", "category", "amount", "payment_method", "expense_date"]
    list_filter = ["company", "category"]
