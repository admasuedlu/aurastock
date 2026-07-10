from django.core.exceptions import ValidationError


def enforce_plan_limit(company, resource: str) -> None:
    """Raises if the company is already at its plan's cap for `resource`
    ("users" | "branches" | "warehouses"). A company with no plan (shouldn't
    happen -- signup always assigns the trial plan -- but legacy rows might)
    is not limited."""
    plan = company.subscription_plan
    if plan is None:
        return

    if resource == "users":
        current, cap, label = company.users.count(), plan.max_users, "users"
    elif resource == "branches":
        current, cap, label = company.tenants_branch_set.count(), plan.max_branches, "branches"
    elif resource == "warehouses":
        current, cap, label = company.inventory_warehouse_set.count(), plan.max_warehouses, "warehouses"
    else:
        raise ValueError(f"Unknown plan-limited resource: {resource}")

    if current >= cap:
        raise ValidationError(
            f"Your {plan.name} plan allows up to {cap} {label} (you have {current}). "
            "Upgrade your plan to add more."
        )
