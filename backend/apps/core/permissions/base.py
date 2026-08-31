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
    "settings.read", "settings.manage",
    "broadcasts.send",
    # CMS do site publico (ver docs/design-handoff/03-cms-especificacao.md).
    "content.read", "content.write", "content.publish",
    "media.manage", "menus.manage", "seo.manage", "plans.manage",
    "requests.read",
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
        # Quem aloca viaturas e motoristas tambem regista quem vende ao balcao.
        # As capacidades existiam mas nenhum papel as dava: para criar um agente
        # POS era preciso o papel de Administrador, com acesso a tudo — incluindo
        # utilizadores, tarifas e financas. A alternativa a uma permissao a mais
        # acaba por ser sempre a permissao a mais perigosa.
        "agents.read", "agents.manage",
        "devices.read", "devices.manage", "validations.read", "reports.read",
        "packages.read", "packages.manage",
        # Avisar por SMS quem vai a bordo quando o autocarro avaria ou a
        # fronteira fecha. E quem gere a operacao que sabe disso primeiro.
        "broadcasts.send",
    ]},
    "support": {"name": "Suporte", "permissions": [
        # Quem atende o passageiro tem de poder corrigir-lhe a conta: um nome
        # mal escrito ou um numero trocado resolvia-se em segundos, mas sem
        # esta capacidade so o Administrador o fazia — e o balcao ficava a
        # espera dele.
        "passengers.read", "passengers.manage",
        "wallets.read", "cards.read", "cards.manage",
        "payments.read", "validations.read", "devices.read",
        # O balcao e quem atende o telefone quando algo corre mal na estrada.
        "broadcasts.send",
    ]},
    "pos_agent": {"name": "Agente POS", "permissions": ["pos.operate"]},
    "auditor": {"name": "Auditor", "permissions": ["audit.read", "reports.read", "reconciliation.read"]},
    # Quem escreve o site nao tem nada que ver a operacao, e o contrario
    # tambem: sem este papel, mudar um preco na pagina publica exigia o papel
    # de Administrador — e com ele vinham as tarifas, as financas e os
    # utilizadores. A especificacao do CMS chama-lhe `conteudo`.
    "conteudo": {"name": "Gestor de Conteudo", "permissions": [
        "content.read", "content.write", "content.publish",
        "media.manage", "menus.manage", "seo.manage", "plans.manage",
        "requests.read",
    ]},
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
