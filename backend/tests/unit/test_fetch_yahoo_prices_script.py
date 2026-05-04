from datetime import date
from pathlib import Path

import pandas as pd

from app.scripts.fetch_yahoo_prices import (
    TickerEntry,
    _to_price_records,
    parse_ticker_file,
    write_price_file,
)


def test_parse_ticker_file_extracts_name_and_symbol(tmp_path: Path) -> None:
    ticker_file = tmp_path / "tiker.txt"
    ticker_file.write_text(
        "Fondsfinans High Yield A (0P000131AW.IR)\n"
        "\n"
        "Invalid line without symbol\n"
        "Heimdal Høyrente A - Rentefond NOK (0P0001ILS7.IR)\n",
        encoding="utf-8",
    )

    entries = parse_ticker_file(ticker_file)

    assert entries == [
        TickerEntry(name="Fondsfinans High Yield A", symbol="0P000131AW.IR"),
        TickerEntry(name="Heimdal Høyrente A - Rentefond NOK", symbol="0P0001ILS7.IR"),
    ]


def test_write_price_file_creates_json_file(tmp_path: Path) -> None:
    entry = TickerEntry(name="Heimdal Høyrente A", symbol="0P0001ILS7.IR")
    records = [
        {"dato": date(2023, 1, 2).isoformat(), "kurs": 100.12},
        {"dato": date(2023, 1, 3).isoformat(), "kurs": 100.17},
    ]

    output_path = write_price_file(tmp_path, entry, records)

    assert output_path.exists()
    assert output_path.name == "heimdal-h-yrente-a-0p0001ils7-ir.json"
    contents = output_path.read_text(encoding="utf-8")
    assert "\"dato\": \"2023-01-02\"" in contents
    assert "\"kurs\": 100.12" in contents


def test_to_price_records_handles_single_ticker_dataframe() -> None:
    index = pd.to_datetime(["2023-01-02", "2023-01-03"])
    columns = pd.MultiIndex.from_tuples([
        ("Close", "0P000131AW.IR"),
        ("Open", "0P000131AW.IR"),
    ])
    frame = pd.DataFrame(
        [[100.12, 100.0], [100.17, 100.1]],
        index=index,
        columns=columns,
    )

    records = _to_price_records(frame)

    assert records == [
        {"dato": "2023-01-02", "kurs": 100.12},
        {"dato": "2023-01-03", "kurs": 100.17},
    ]
