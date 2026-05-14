from __future__ import annotations

CANONICAL_BY_SYMBOL: dict[str, tuple[str, str]] = {
    "0P000131AW.IR": ("Fondsfinans High Yield", "FHY"),
    "0P0001ILS7.IR": ("Heimdal Høyrente", "HHR"),
    "0P0001PLOM.IR": ("Kraft Nordic Bonds B", "KNB"),
    "0P0001SCH2.IR": ("Kraft Høyrente D", "KHD"),
}

CANONICAL_BY_TICKER: dict[str, str] = {
    "FHY": "Fondsfinans High Yield",
    "HHR": "Heimdal Høyrente",
    "HHRP": "Heimdal Høyrente Plus",
    "KNB": "Kraft Nordic Bonds B",
    "KHD": "Kraft Høyrente D",
}

NAME_ALIASES: dict[str, tuple[str, str]] = {
    "heimdal høyrente plus": ("Heimdal Høyrente Plus", "HHRP"),
    "heimdal høyrente pluss": ("Heimdal Høyrente Plus", "HHRP"),
}


def canonicalize_fund(name: str, ticker_or_symbol: str) -> tuple[str, str]:
    """Return canonical fund name and ticker from name or symbol input."""
    key = ticker_or_symbol.strip().upper()

    if key in CANONICAL_BY_SYMBOL:
        return CANONICAL_BY_SYMBOL[key]

    if key in CANONICAL_BY_TICKER:
        return CANONICAL_BY_TICKER[key], key

    name_key = " ".join(name.strip().lower().split())
    if name_key in NAME_ALIASES:
        return NAME_ALIASES[name_key]

    return name.strip(), key
