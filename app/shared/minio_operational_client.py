"""Cliente de MinIO operacional — un objeto JSON por registro, con escritura
condicional por ETag para concurrencia (RC-OP-001/002).

Reemplaza a PocketBase como motor de escritura para las colecciones
OPERACIONALES (ver plan de migración). El SDK `minio` no expone escritura
condicional en `put_object` (solo en `copy_object`, vía `CopySource`), así
que este cliente usa `boto3` — confirmado con un spike que `minio-travel`
soporta If-Match/If-None-Match nativamente en PutObject (HTTP 412 real ante
conflicto, sin necesitar versionado de bucket).

`minio_dims_reader.py` sigue usando `minio` porque solo lee — no se toca.
"""

from __future__ import annotations

import asyncio
import io
import json
import random
import secrets
from typing import Callable

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.shared.config import get_settings

_ALFABETO_ID = "abcdefghijklmnopqrstuvwxyz0123456789"

MAX_REINTENTOS = 20
_BACKOFF_BASE_SEGUNDOS = 0.03
_BACKOFF_MAX_SEGUNDOS = 1.0


class ConflictoConcurrencia(Exception):
    """Se agotaron los reintentos por conflicto de escritura concurrente."""


class RegistroNoExiste(Exception):
    pass


class RegistroYaExiste(Exception):
    pass


def _client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access,
        aws_secret_access_key=settings.minio_secret,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _key(entidad: str, id_: str) -> str:
    return f"operacional/{entidad}/{id_}.json"


def generar_id() -> str:
    """Id estilo PocketBase (15 caracteres) — a diferencia de PocketBase, un
    objeto MinIO necesita su id ANTES de escribirse (es parte de la key),
    así que el caller lo genera en vez de recibirlo de vuelta al crear."""
    return "".join(secrets.choice(_ALFABETO_ID) for _ in range(15))


def _http_status(error: ClientError) -> int:
    return error.response["ResponseMetadata"]["HTTPStatusCode"]


def _get_sync(bucket: str, entidad: str, id_: str) -> tuple[dict | None, str | None]:
    client = _client()
    try:
        resp = client.get_object(Bucket=bucket, Key=_key(entidad, id_))
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None, None
        raise
    return json.loads(resp["Body"].read()), resp["ETag"]


def _put_sync(
    bucket: str, entidad: str, id_: str, data: dict,
    *, if_match: str | None = None, if_absent: bool = False,
) -> None:
    client = _client()
    kwargs: dict = {}
    if if_absent:
        kwargs["IfNoneMatch"] = "*"
    elif if_match:
        kwargs["IfMatch"] = if_match
    client.put_object(
        Bucket=bucket, Key=_key(entidad, id_),
        Body=io.BytesIO(json.dumps(data).encode()),
        ContentType="application/json",
        **kwargs,
    )


async def obtener(entidad: str, id_: str) -> dict | None:
    """Lee un registro; None si no existe."""
    settings = get_settings()
    data, _ = await asyncio.to_thread(
        _get_sync, settings.minio_bucket_travel_operational, entidad, id_
    )
    return data


def _list_keys_sync(bucket: str, prefix: str) -> list[str]:
    client = _client()
    paginator = client.get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


async def listar_todos(entidad: str) -> list[dict]:
    """Lista TODOS los registros de una entidad (sin filtro server-side).

    El volumen de las entidades operacionales migradas hasta ahora es
    bajo/medio (cientos de registros) — traer todo y filtrar en Python es
    aceptable, mismo criterio que ya usan varios repos de PocketBase para
    colecciones chicas (ej. `CrucerosRepository.listar_cruceros`). Si una
    entidad crece mucho, considerar particionar por prefijo o mantener un
    índice secundario en vez de escalar este mismo patrón indefinidamente.
    """
    settings = get_settings()
    bucket = settings.minio_bucket_travel_operational
    prefix = f"operacional/{entidad}/"
    keys = await asyncio.to_thread(_list_keys_sync, bucket, prefix)

    async def _leer(key: str) -> dict | None:
        id_ = key[len(prefix):-len(".json")]
        return await obtener(entidad, id_)

    resultados = await asyncio.gather(*(_leer(k) for k in keys))
    return [r for r in resultados if r is not None]


async def eliminar(entidad: str, id_: str) -> None:
    settings = get_settings()

    def _delete() -> None:
        client = _client()
        client.delete_object(Bucket=settings.minio_bucket_travel_operational, Key=_key(entidad, id_))

    await asyncio.to_thread(_delete)


def _key_archivo(entidad: str, id_: str, filename: str) -> str:
    return f"operacional/{entidad}/{id_}/{filename}"


async def subir_archivo(entidad: str, id_: str, filename: str, contenido: bytes, content_type: str) -> None:
    """Sube un binario propio (PDF de factura/voucher, etc.) — objeto
    aparte del JSON del registro, mismo bucket operacional. Reemplaza el
    patrón `update_record_con_archivo` de PocketBase (campo `file`), que ya
    no aplica a colecciones OPERACIONAL migradas a MinIO."""
    settings = get_settings()

    def _put() -> None:
        client = _client()
        client.put_object(
            Bucket=settings.minio_bucket_travel_operational,
            Key=_key_archivo(entidad, id_, filename),
            Body=io.BytesIO(contenido),
            ContentType=content_type,
        )

    await asyncio.to_thread(_put)


async def descargar_archivo(entidad: str, id_: str, filename: str) -> bytes:
    settings = get_settings()

    def _get() -> bytes:
        client = _client()
        resp = client.get_object(
            Bucket=settings.minio_bucket_travel_operational, Key=_key_archivo(entidad, id_, filename)
        )
        return resp["Body"].read()

    return await asyncio.to_thread(_get)


async def crear(entidad: str, id_: str, data: dict) -> dict:
    """Crea un registro nuevo. Falla con `RegistroYaExiste` si el id ya existe
    (evita pisar un registro por colisión de id generado concurrentemente)."""
    settings = get_settings()
    try:
        await asyncio.to_thread(
            _put_sync, settings.minio_bucket_travel_operational, entidad, id_, data,
            if_absent=True,
        )
    except ClientError as e:
        if _http_status(e) == 412:
            raise RegistroYaExiste(f"{entidad}/{id_} ya existe")
        raise
    return data


async def actualizar_con_reintento(
    entidad: str, id_: str, mutar: Callable[[dict], dict]
) -> dict:
    """Lee-modifica-escribe con reintento optimista (If-Match).

    `mutar(data) -> data` recibe una copia del registro actual y devuelve la
    versión modificada; puede lanzar cualquier excepción propia del dominio
    (ej. cupo insuficiente) para abortar sin reintentar — solo el conflicto
    de escritura concurrente (412) dispara reintento.
    """
    settings = get_settings()
    bucket = settings.minio_bucket_travel_operational
    for intento in range(MAX_REINTENTOS):
        data, etag = await asyncio.to_thread(_get_sync, bucket, entidad, id_)
        if data is None:
            raise RegistroNoExiste(f"{entidad}/{id_} no existe")
        nuevo = mutar(dict(data))
        try:
            await asyncio.to_thread(
                _put_sync, bucket, entidad, id_, nuevo, if_match=etag
            )
            return nuevo
        except ClientError as e:
            if _http_status(e) == 412:
                espera = min(_BACKOFF_BASE_SEGUNDOS * (2 ** intento), _BACKOFF_MAX_SEGUNDOS)
                await asyncio.sleep(espera * (0.5 + random.random()))
                continue
            raise
    raise ConflictoConcurrencia(
        f"No se pudo actualizar {entidad}/{id_} tras {MAX_REINTENTOS} intentos (alta contención)"
    )
