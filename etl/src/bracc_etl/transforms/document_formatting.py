import re


def strip_document(doc: str | None) -> str:
    if not doc:
        return ""
    return re.sub(r"[^0-9]", "", doc)


def format_cpf(cpf: str | None) -> str:
    digits = strip_document(cpf)
    if len(digits) != 11:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def normalize_cnpj(cnpj: str | None) -> str:
    """Remove CNPJ punctuation while preserving letters and leading zeros."""
    return re.sub(r"[.\-/]", "", (cnpj or "").strip()).upper()


def format_cnpj(cnpj: str | None) -> str:
    digits = normalize_cnpj(cnpj)
    if not re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", digits):
        return digits
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _cpf_check_digits(digits: str) -> bool:
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    total = sum(int(digits[i]) * (10 - i) for i in range(9))
    d1 = 11 - (total % 11)
    d1 = 0 if d1 >= 10 else d1
    if int(digits[9]) != d1:
        return False
    total = sum(int(digits[i]) * (11 - i) for i in range(10))
    d2 = 11 - (total % 11)
    d2 = 0 if d2 >= 10 else d2
    return int(digits[10]) == d2


def validate_cpf(cpf: str | None) -> bool:
    digits = re.sub(r"[.\-]", "", (cpf or "").strip())
    return bool(re.fullmatch(r"[0-9]{11}", digits)) and _cpf_check_digits(digits)


def _cnpj_check_digits(digits: str) -> bool:
    if not re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", digits) or len(set(digits)) == 1:
        return False
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum((ord(digits[i]) - 48) * weights1[i] for i in range(12))
    d1 = 11 - (total % 11)
    d1 = 0 if d1 >= 10 else d1
    if int(digits[12]) != d1:
        return False
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum((ord(digits[i]) - 48) * weights2[i] for i in range(13))
    d2 = 11 - (total % 11)
    d2 = 0 if d2 >= 10 else d2
    return int(digits[13]) == d2


def validate_cnpj(cnpj: str | None) -> bool:
    digits = normalize_cnpj(cnpj)
    return _cnpj_check_digits(digits)


def classify_document(doc: str | None) -> str:
    """Classify a Brazilian document string for identity handling.

    Returns one of:
    - cpf_valid: 11-digit CPF-like document (masked not allowed)
    - cpf_partial: masked/partial CPF (LGPD style, 6 visible digits)
    - cnpj_valid: 14-digit CNPJ-like document
    - invalid: anything else
    """
    raw = (doc or "").strip()
    digits = strip_document(raw)
    has_mask = "*" in raw

    if has_mask and len(digits) == 6:
        return "cpf_partial"
    if re.fullmatch(r"[0-9]{11}", re.sub(r"[.\-]", "", raw)):
        return "cpf_valid"
    if re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", normalize_cnpj(raw)):
        return "cnpj_valid"
    return "invalid"
