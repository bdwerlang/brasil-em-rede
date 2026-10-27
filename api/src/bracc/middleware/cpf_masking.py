"""Middleware that masks CPF numbers in API responses to protect personal data.

CPF (Cadastro de Pessoa Fisica) is an 11-digit Brazilian tax ID.
Politically Exposed Persons (PEPs) have their CPFs kept visible.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from bracc.constants import PEP_ROLES

if TYPE_CHECKING:
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.requests import Request

# Matches 11-digit CPF in formatted (123.456.789-00) or raw (12345678900) form.
# Uses negative lookbehind/lookahead to avoid matching inside longer digit sequences
# (e.g. 14-digit CNPJ).
_CPF_FORMATTED = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_CPF_RAW = re.compile(r"(?<!\d)\d{11}(?!\d)")
_CNPJ_RAW = re.compile(r"[A-Za-z0-9]{12}[0-9]{2}")
_CNPJ_FIELDS = {
    "cnpj", "company_cnpj", "agency_cnpj", "supplier_cnpj", "winner_cnpj",
    "fund_cnpj", "administrator_cnpj", "manager_cnpj", "holding_cnpj", "party_cnpj",
    "mentioned_cnpj", "cnpj_empresa", "cnpj_socia", "cnpj_favorecido", "cnpj_contratada",
    "cnpj_fornecedor", "cnpj_vencedor", "numero_cnpj", "numero_cnpj_entidade",
}


def mask_formatted_cpf(cpf: str) -> str:
    """Mask a formatted CPF, keeping only the last 4 visible digits.

    Example: 123.456.789-00 -> ***.***.789-00
    """
    return f"***.***.{cpf[8:]}"


def mask_raw_cpf(cpf: str) -> str:
    """Mask a raw 11-digit CPF, keeping only the last 4 digits.

    Example: 12345678900 -> *******8900
    """
    return f"*******{cpf[7:]}"


def _is_pep_record(record: dict[str, Any]) -> bool:
    """Determine whether a JSON record describes a PEP.

    Checks for explicit ``is_pep`` boolean or political keywords in the
    ``role`` / ``cargo`` fields.
    """
    if record.get("is_pep") is True:
        return True

    for field in ("role", "cargo"):
        value = record.get(field)
        if isinstance(value, str) and any(kw in value.strip().lower() for kw in PEP_ROLES):
            return True

    return False


def _collect_pep_cpfs(data: Any) -> set[str]:
    """Walk a JSON structure and return the set of CPF strings belonging to PEPs."""
    pep_cpfs: set[str] = set()

    if isinstance(data, dict):
        if _is_pep_record(data):
            cpf_val = data.get("cpf")
            if isinstance(cpf_val, str) and cpf_val:
                # Normalise to digits-only for comparison.
                pep_cpfs.add(re.sub(r"\D", "", cpf_val))
        for value in data.values():
            pep_cpfs |= _collect_pep_cpfs(value)
    elif isinstance(data, list):
        for item in data:
            pep_cpfs |= _collect_pep_cpfs(item)

    return pep_cpfs


def _digits_only(cpf: str) -> str:
    return re.sub(r"\D", "", cpf)


def _mask_text(text: str, safe: set[str]) -> str:
    def replace_formatted(match: re.Match[str]) -> str:
        if _digits_only(match.group()) in safe:
            return match.group()
        return mask_formatted_cpf(match.group())

    def replace_raw(match: re.Match[str]) -> str:
        return match.group() if match.group() in safe else mask_raw_cpf(match.group())

    return _CPF_RAW.sub(replace_raw, _CPF_FORMATTED.sub(replace_formatted, text))


def _mask_json_value(value: Any, safe: set[str], field: str = "") -> Any:
    if isinstance(value, dict):
        return {key: _mask_json_value(item, safe, key) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_json_value(item, safe, field) for item in value]
    if isinstance(value, str):
        normalized = re.sub(r"[.\-/]", "", value)
        if field.lower() in _CNPJ_FIELDS and _CNPJ_RAW.fullmatch(normalized):
            return value
        return _mask_text(value, safe)
    if isinstance(value, int) and not isinstance(value, bool):
        masked = _mask_text(str(value), safe)
        return value if masked == str(value) else masked
    return value


def mask_cpfs_in_json(text: str, pep_cpfs: set[str] | None = None) -> str:
    """Mask CPF-like text, preserving complete CNPJ only in known CNPJ fields."""
    safe = pep_cpfs or set()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return _mask_text(text, safe)
    masked = _mask_json_value(data, safe)
    if masked == data:
        return text
    return json.dumps(masked, ensure_ascii=False, separators=(",", ":"))


class CPFMaskingMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that masks CPF numbers in JSON responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Read the full body from the streaming response.
        body_bytes = b""
        if hasattr(response, "body_iterator"):
            chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    chunks.append(chunk.encode("utf-8"))
                elif isinstance(chunk, bytes):
                    chunks.append(chunk)
                else:
                    chunks.append(bytes(chunk))
            body_bytes = b"".join(chunks)
        else:
            body_bytes = getattr(response, "body", b"")

        if not body_bytes:
            return response

        body_text = body_bytes.decode("utf-8")

        # Parse JSON to discover PEP CPFs, then mask the rest.
        pep_cpfs: set[str] = set()
        try:
            data = json.loads(body_text)
            pep_cpfs = _collect_pep_cpfs(data)
        except (json.JSONDecodeError, TypeError):
            pass

        masked_text = mask_cpfs_in_json(body_text, pep_cpfs)
        masked_bytes = masked_text.encode("utf-8")

        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=masked_bytes,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
