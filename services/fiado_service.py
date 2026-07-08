from datetime import date, datetime
from database import get_db


def calcular_status_fiado(data_vencimento):
    if not data_vencimento:
        return "normal", None
    try:
        venc = datetime.strptime(data_vencimento, "%Y-%m-%d").date()
        dias = (venc - date.today()).days
        if dias <= 0:
            return "vencido", dias
        elif dias <= 5:
            return "alerta", dias
        elif dias <= 10:
            return "atencao", dias
        return "normal", dias
    except (ValueError, TypeError):
        return "normal", None


def tem_fiado_vencido(cliente_id):
    db = get_db()
    hoje = date.today().isoformat()
    vencido = db.execute("""
        SELECT COUNT(*) as c FROM fiado
        WHERE cliente_id=? AND tipo='compra' AND (valor - valor_pago) > 0.01
        AND data_vencimento IS NOT NULL AND data_vencimento < ?
    """, (cliente_id, hoje)).fetchone()["c"]
    return bool(vencido)
