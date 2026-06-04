from rest_framework.permissions import BasePermission

ALL_CAPABILITIES = [
    "passengers.read", "passengers.manage",
    "wallets.read", "wallets.manage",
    "cards.read", "cards.manage",
    "routes.read", "routes.manage",
    "stops.read", "stops.manage",
    "trips.read", "trips.manage",
    "fares.read", "fares.manage",
    "vehicles.read", "vehicles.manage",
    "drivers.read", "drivers.manage",
    "agents.read", "agents.manage",
    "devices.read", "devices.manage",
    "payments.read", "payments.manage",
    "validations.read",
    "reports.read", "reconciliation.read",
    "audit.read",
    "users.read", "users.manage",
    "roles.read", "roles.manage",
    "pos.operate",
    "packages.read", "packages.manage",
    "imports.manage",
]

DEFAULT_ROLES = {
    "admin": {"name": "Administrador", "permissions": ["*"]},
    "financial_manager": {"name": "Gestor Financeiro", "permissions": [
        "passengers.read", "wallets.read", "wallets.manage",
        "payments.read", "payments.manage", "reports.read", "reconciliation.read",
    ]},
    "operations_manager": {"name": "Gestor Operacional", "permissions": [
        "passengers.read", "routes.read", "routes.manage", "stops.read", "stops.manage",
        "trips.read", "trips.manage", "fares.read", "fares.manage",
        "vehicles.read", "vehicles.manage", "drivers.read", "drivers.manage",
        "devices.read", "devices.manage", "validations.read", "reports.read",
        "packages.read", "packages.manage",
    ]},
    "support": {"name": "Suporte", "permissions": [
        "passengers.read", "wallets.read", "cards.read", "cards.manage",
        "payments.read", "validations.read", "devices.read",
    ]},
    "pos_agent": {"name": "Agente POS", "permissions": ["pos.operate"]},
    "auditor": {"name": "Auditor", "permissions": ["audit.read", "reports.read", "reconciliation.read"]},
}


def resolve_user_capabilities(user):
    if getattr(user, "is_superuser", False):
        return ["*"]
    if hasattr(user, "get_capabilities"):
        return user.get_capabilities()
    return []


def has_capabilities(user, required_capabilities):
    required = tuple(required_capabilities or ())
    if not required:
        return True
    if getattr(user, "is_superuser", False):
        return True
    capabilities = set(resolve_user_capabilities(user))
    if "*" in capabilities:
        return True
    return all(cap in capabilities for cap in required)


class HasCapabilities(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        required = ()
        if hasattr(view, "get_required_capabilities"):
            required = view.get_required_capabilities()
        else:
            required = getattr(view, "required_capabilities", ())
        return has_capabilities(request.user, required)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
