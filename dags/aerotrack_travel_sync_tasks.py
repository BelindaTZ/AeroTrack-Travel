"""
AeroTrack Travel — Funciones del DAG puente aerotrack_travel_sync_dims
========================================================================
Dispara los DAGs de AeroTrack Analytics (minio-elt) vía su API de Airflow
y sincroniza el modelo dimensional resultante a minio-travel.

Esta es la ÚNICA parte de Travel que necesita que Analytics (Airflow +
MinIO) esté corriendo, y solo mientras se ejecuta este DAG puntual — no
es una dependencia permanente del resto del proyecto.
"""

from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime

# Únicos contenedores de Analytics (minio-elt) que este DAG realmente
# necesita. Deliberadamente NO se tocan prometheus/grafana/fastapi-app/
# aerotrack-setup — no participan del ELT ni de la cobertura global.
CONTENEDORES_ANALYTICS_NECESARIOS = [
    "postgres-airflow",
    "minio",
    "pocketbase",
    "airflow-webserver",
    "airflow-scheduler",
]


def asegurar_analytics_arriba(timeout_segundos: int = 120) -> None:
    """Arranca (si no están corriendo) solo los contenedores de Analytics
    estrictamente necesarios, usando el socket de Docker del host — montado
    ÚNICAMENTE en airflow-scheduler-travel, no en el resto de Travel.

    Si algún contenedor no existe (nunca se corrió `docker compose up` en
    minio-elt al menos una vez), falla con un mensaje explícito en vez de
    un timeout confuso más adelante."""
    import docker
    import requests

    import config

    cliente = docker.from_env()

    print(f"[SYNC] Verificando contenedores de Analytics: {CONTENEDORES_ANALYTICS_NECESARIOS}")
    faltantes = []
    for nombre in CONTENEDORES_ANALYTICS_NECESARIOS:
        try:
            contenedor = cliente.containers.get(nombre)
        except docker.errors.NotFound:
            faltantes.append(nombre)
            continue
        if contenedor.status != "running":
            print(f"[SYNC] Arrancando '{nombre}' (estaba '{contenedor.status}')...")
            contenedor.start()
        else:
            print(f"[SYNC] '{nombre}' ya está corriendo")

    if faltantes:
        raise RuntimeError(
            f"Estos contenedores de Analytics no existen: {faltantes}. "
            f"Corre 'docker compose up -d' en minio-elt al menos una vez antes de usar este DAG."
        )

    print(f"[SYNC] Esperando a que la API de Airflow de Analytics responda (timeout {timeout_segundos}s)...")
    deadline = time.time() + timeout_segundos
    while time.time() < deadline:
        try:
            r = requests.get(f"{config.ANALYTICS_AIRFLOW_URL}/health", timeout=5)
            if r.status_code == 200:
                print("[SYNC] ✅ Analytics arriba y respondiendo")
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)

    raise TimeoutError(f"Analytics no respondió en {timeout_segundos}s tras arrancar los contenedores.")


def disparar_dag_analytics(dag_id: str, timeout_minutos: int = 90, poll_segundos: int = 15) -> str:
    """Dispara un DAG en el Airflow de Analytics vía API REST y espera a
    que termine (success/failed) o se agote el timeout. Lanza una
    excepción si Analytics no está accesible, si el DAG falla, o si no
    termina a tiempo."""
    import requests

    import config

    base = config.ANALYTICS_AIRFLOW_URL
    auth = (config.ANALYTICS_AIRFLOW_USER, config.ANALYTICS_AIRFLOW_PASSWORD)
    run_id = f"travel_trigger_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"[SYNC] Disparando '{dag_id}' en Analytics ({base})...")
    try:
        resp = requests.post(
            f"{base}/api/v1/dags/{dag_id}/dagRuns",
            auth=auth,
            json={"dag_run_id": run_id},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"No se pudo disparar '{dag_id}' en Analytics ({base}). "
            f"¿Está corriendo el stack de minio-elt (docker compose up)? Error: {e}"
        ) from e

    print(f"[SYNC] dag_run_id={run_id} — esperando a que termine (timeout {timeout_minutos} min)...")

    deadline = time.time() + timeout_minutos * 60
    while time.time() < deadline:
        r = requests.get(f"{base}/api/v1/dags/{dag_id}/dagRuns/{run_id}", auth=auth, timeout=30)
        r.raise_for_status()
        estado = r.json().get("state")

        if estado == "success":
            print(f"[SYNC] ✅ '{dag_id}' ({run_id}) completado exitosamente")
            return estado
        if estado == "failed":
            raise RuntimeError(
                f"'{dag_id}' ({run_id}) falló en Analytics. Revisa su Airflow UI (http://localhost:8080)."
            )

        time.sleep(poll_segundos)

    raise TimeoutError(f"'{dag_id}' ({run_id}) no terminó dentro de {timeout_minutos} minutos.")


def sincronizar_dims_a_travel() -> dict:
    """Copia todos los objetos de aerotrack-dims (Analytics) a
    aerotrack-travel-dims (Travel). Sobreescribe lo que ya haya."""
    from minio import Minio

    import config

    origen = Minio(
        config.ANALYTICS_MINIO_ENDPOINT,
        access_key=config.ANALYTICS_MINIO_ACCESS,
        secret_key=config.ANALYTICS_MINIO_SECRET,
        secure=False,
    )
    destino = Minio(
        config.MINIO_ENDPOINT,
        access_key=config.MINIO_ACCESS,
        secret_key=config.MINIO_SECRET,
        secure=False,
    )

    bucket_origen = config.ANALYTICS_MINIO_BUCKET_DIMS
    bucket_destino = config.MINIO_BUCKET_TRAVEL_DIMS

    if not destino.bucket_exists(bucket_destino):
        destino.make_bucket(bucket_destino)

    objetos = list(origen.list_objects(bucket_origen, recursive=True))
    print(f"[SYNC] Sincronizando {len(objetos)} archivos: s3://{bucket_origen}/ → s3://{bucket_destino}/ (minio-travel)")

    total_bytes = 0
    for obj in objetos:
        tmp = tempfile.mktemp()
        origen.fget_object(bucket_origen, obj.object_name, tmp)
        destino.fput_object(bucket_destino, obj.object_name, tmp)
        total_bytes += os.path.getsize(tmp)
        os.remove(tmp)
        print(f"[SYNC]   {obj.object_name} ({obj.size / 1024:.0f} KB)")

    print(f"[SYNC] ✅ {len(objetos)} archivos ({total_bytes / 1024 / 1024:.1f} MB) → s3://{bucket_destino}/")
    return {"archivos": len(objetos), "bytes": total_bytes}
