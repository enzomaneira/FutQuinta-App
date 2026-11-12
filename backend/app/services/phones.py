"""Normalização de telefone para E.164 (+5511987654321).

Aceita o que o organizador digitar no celular: "(11) 98765-4321",
"11987654321", "+55 11 98765-4321", "5511987654321". Sem DDI, assume Brasil.
"""

import re

from app.services.errors import DomainError

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
BRAZIL = "55"


def normalize_phone(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    text = raw.strip()
    digits = re.sub(r"\D", "", text)

    if text.startswith("+"):
        candidate = "+" + digits
    elif text.startswith("00"):  # discagem internacional: 00 + DDI
        candidate = "+" + digits[2:]
    elif len(digits) in (10, 11):  # DDD + número (fixo ou celular)
        candidate = "+" + BRAZIL + digits
    elif len(digits) in (12, 13) and digits.startswith(BRAZIL):
        candidate = "+" + digits
    else:
        candidate = "+" + digits

    if not E164.match(candidate):
        raise DomainError("Telefone inválido. Use DDD + número, ex.: (11) 98765-4321")
    return candidate
