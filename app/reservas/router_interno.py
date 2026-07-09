"""RF-RES-007 — disparado por el scheduler (Airflow), sin input de usuario.

Nota de seguridad: en esta sesión el endpoint no exige autenticación de
usuario porque no hay un actor humano detrás — lo llama un proceso interno
por temporizador (`dags/dag_expirar_reservas_pendientes.py`). En un
despliegue real, este endpoint debe protegerse a nivel de red (no expuesto
públicamente) o con un token compartido — no implementado en esta sesión.
"""

from fastapi import APIRouter

from app.reservas.services.expiracion_service import expirar_pendientes

router = APIRouter(prefix="/internal/reservas")


@router.post("/expirar-pendientes")
async def expirar_pendientes_endpoint() -> dict:
    cantidad = await expirar_pendientes()
    return {"expiradas": cantidad}
