from .auth_routes import register_auth_routes
from .dashboard_routes import register_dashboard_routes
from .mesas_routes import register_mesas_routes
from .vendas_routes import register_vendas_routes
from .produtos_routes import register_produtos_routes
from .estoque_routes import register_estoque_routes
from .clientes_routes import register_clientes_routes
from .caixa_routes import register_caixa_routes
from .admin_routes import register_admin_routes
from .relatorios_routes import register_relatorios_routes

__all__ = [
    "register_auth_routes", "register_dashboard_routes",
    "register_mesas_routes", "register_vendas_routes",
    "register_produtos_routes", "register_estoque_routes",
    "register_clientes_routes", "register_caixa_routes",
    "register_admin_routes", "register_relatorios_routes",
]
