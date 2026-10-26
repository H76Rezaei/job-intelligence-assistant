"""Rules on job titles and company names: when two postings are the same job,
and when a title calls the role senior.

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


# Words in a title that open the role to non-seniors as well ("Junior/Senior Developer")
_OPEN_TO_NON_SENIORS = ("junior", "mid", "entry", "einsteiger", "berufseinsteiger")


def _has_word(title: str, word: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(word.lower())}(?!\w)", title.lower()) is not None


def is_senior_title(title: str, senior_words: list[str]) -> bool:
    """The title calls the role senior; the description is never considered.

    A senior word alone in brackets, as in "(Senior) Data Scientist", marks the
    level as optional, so it does not count.
    """
    title = title.lower()
    if any(_has_word(title, word) for word in _OPEN_TO_NON_SENIORS):
        return False
    for word in senior_words:
        title = re.sub(rf"\(\s*{re.escape(word.lower())}\s*\)", " ", title)
    return any(_has_word(title, word) for word in senior_words)
