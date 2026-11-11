"""Contacts of the back panel, recognised from how they are written.

Same rules as the lookbook: ``monpiz@monpiz.it`` is an e-mail,
``+39 376 ...`` a phone number (also on WhatsApp),
``instagram.com/monpiz_official`` the Instagram profile (shown as
``@monpiz_official``), any other address the web site.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)
_PHONE = re.compile(r"^\+?[\d\s]{6,}$")
_WEB = re.compile(r"^(https?://)?[\w-]+(\.[\w-]+)+(/\S*)?$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Contact:
    label: str  # "Email", "Telefono e WhatsApp", "Instagram", "Sito"
    text: str  # as printed
    href: str | None


def contact(raw: str) -> Contact:
    text = raw.strip()
    if _EMAIL.match(text):
        return Contact("Email", text, f"mailto:{text}")
    if _PHONE.match(text):
        digits = re.sub(r"[^\d+]", "", text)
        return Contact(
            "Telefono e WhatsApp", text, f"tel:{digits if digits.startswith('+') else '+39' + digits}"
        )
    if _WEB.match(text):
        href = text if text.startswith("http") else f"https://{text}"
        parts = urlsplit(href)
        host = parts.netloc.removeprefix("www.")
        path = parts.path.strip("/")
        if host == "instagram.com" and path:
            return Contact("Instagram", f"@{path.split('/')[0]}", href)
        return Contact("Sito", host + (f"/{path}" if path else ""), href)
    return Contact("", text, None)
