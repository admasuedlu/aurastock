"""Default permission catalog and starter role templates.

Kept as plain data (not fixtures) so it's easy to extend as new modules
land. `seed_permissions` populates the global `Permission` table;
`seed_default_roles` grants a sensible subset to each starter role when a
new company signs up.
"""

MODULES = [
    "products", "inventory", "warehouses", "purchases", "suppliers",
    "sales", "customers", "pos", "accounting", "reports", "users", "settings",
]
ACTIONS = ["view", "add", "change", "delete", "approve"]


def permission_code(module: str, action: str) -> str:
    return f"{module}.{action}"


def all_permission_codes():
    return [permission_code(m, a) for m in MODULES for a in ACTIONS]


# role name -> list of (module, [actions]) grants. "*" means all actions.
ROLE_TEMPLATES = {
    "Owner": {m: ["*"] for m in MODULES},
    "Admin": {m: ["*"] for m in MODULES},
    "Inventory Manager": {
        "products": ["*"], "inventory": ["*"], "warehouses": ["*"], "reports": ["view"],
    },
    "Warehouse Manager": {
        "inventory": ["*"], "warehouses": ["*"], "products": ["view"], "reports": ["view"],
        "purchases": ["view", "change"],
    },
    "Sales Person": {
        "sales": ["view", "add", "change"], "customers": ["*"], "products": ["view"],
        "reports": ["view"],
    },
    "Cashier": {
        "pos": ["*"], "sales": ["view", "add"], "customers": ["view", "add"],
        "inventory": ["view"],
    },
    "Accountant": {
        "accounting": ["*"], "reports": ["view"], "sales": ["view"], "purchases": ["view"],
    },
    "Procurement Officer": {
        "purchases": ["*"], "suppliers": ["*"], "products": ["view"], "reports": ["view"],
    },
    "Delivery Staff": {
        "inventory": ["view"], "sales": ["view"],
    },
}


def resolve_codes_for_role(template: dict) -> list[str]:
    codes = []
    for module, actions in template.items():
        if actions == ["*"]:
            codes.extend(permission_code(module, a) for a in ACTIONS)
        else:
            codes.extend(permission_code(module, a) for a in actions)
    return codes
