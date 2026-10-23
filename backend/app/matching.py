"""Cleanup rules that decide when two postings are the same job.

The cleaned values are matching keys only; original names are stored and shown.
"""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# "(m/w/d)", "(w/m/d)", "(m/f/d)", "(m/w/divers)", "(all genders)", "(gn)",
# or an unbracketed "m/w/d" standing alone
_GENDER_TAG = re.compile(
    r"\(\s*(?:[mwfdx]\s*/\s*[mwfdx](?:\s*/\s*[a-z*]+)?|all genders|gn\*?)\s*\)"
    r"|(?<![\w/])[mwfd]\s*/\s*[mwfd]\s*/\s*[dx](?![\w/])",
    re.IGNORECASE,
)

# A legal form at the end of a company name, optionally as "... & Co. KG"
_LEGAL_FORM = re.compile(
    r"[\s,]+(?:"
    r"(?:ggmbh|gmbh|mbh|ag|se|ug|ltd\.?|inc\.?|llc|b\.\s?v\.)(?:\s*&\s*co\.?\s*(?:kgaa|kg|ohg))?"
    r"|ug \(haftungsbeschränkt\)|kgaa|kg|ohg|e\.\s?v\."
    r")$"
)

_TRACKING_PARAMS = re.compile(r"^(utm_.*|gclid|fbclid|trk|trackingid)$", re.IGNORECASE)


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(title: str) -> str:
    cleaned = _GENDER_TAG.sub(" ", title.lower())
    return _collapse(cleaned).strip(" -–|,")


def normalize_company_name(name: str) -> str:
    cleaned = _collapse(name.lower())
    # Repeat for names like "Foo AG, GmbH"
    while (stripped := _LEGAL_FORM.sub("", cleaned)) != cleaned:
        cleaned = stripped
    return cleaned.rstrip(" ,")


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _TRACKING_PARAMS.match(k)
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(query),
            "",
        )
    )
