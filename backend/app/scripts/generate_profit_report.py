"""Generate a profit/loss report for all funds in the portfolio."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal, create_db_and_tables
from app.models.fund import Fund
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.rate_repository import RateRepository
from app.repositories.transaction_repository import TransactionRepository
from app.scripts.fund_identity import CANONICAL_BY_TICKER
from app.services.interest_service import InterestService
from app.services.portfolio_analytics_service import PortfolioAnalyticsService

DECIMAL_ZERO = Decimal("0")
COL_WIDTH = 16
TICKERS = list(CANONICAL_BY_TICKER.keys())


def _nok(value: Decimal) -> str:
    """Format a numeric value as NOK with no decimal places."""
    return f"{value:,.0f} kr"


def _pct(value: Decimal | None) -> str:
    """Format an optional percentage value for report output."""
    if value is None:
        return "  N/A"
    return f"{value:+.2f}%"


def _row(label: str, *cols: str) -> str:
    """Build one aligned report row with label and columns."""
    first = f"  {label:<28}"
    rest = "".join(f"{c:>{COL_WIDTH}}" for c in cols)
    return first + rest


def _divider(n_cols: int) -> str:
    """Return a horizontal divider sized for current column count."""
    return "-" * (30 + COL_WIDTH * n_cols)


def main() -> None:
    """Generate and print a portfolio profit report to stdout."""
    create_db_and_tables()
    as_of = date.today()

    with SessionLocal() as session:
        funds = list(
            session.scalars(
                select(Fund).where(Fund.ticker.in_(TICKERS)).order_by(Fund.ticker.asc())
            )
        )
        if not funds:
            print("No funds found. Run seed_portfolio_data first.")
            return

        svc = PortfolioAnalyticsService(
            FundRepository(session),
            TransactionRepository(session),
            PriceRepository(session),
            RateRepository(session),
            InterestService(),
        )

        summaries = []
        for fund in funds:
            try:
                s = svc.get_fund_summary(fund.id, as_of_date=as_of)
                summaries.append(s)
            except Exception as exc:  # noqa: BLE001
                print(f"  [WARN] Could not compute {fund.ticker}: {exc}")

        if not summaries:
            print("No data available.")
            return

        tickers = [s.ticker or s.fund_name[:6] for s in summaries]
        n = len(tickers)

        print()
        print("=" * (30 + COL_WIDTH * n))
        print(f"  PROFIT RAPPORT — per {as_of:%d.%m.%Y}")
        print("=" * (30 + COL_WIDTH * n))
        print(_row("", *tickers))
        print(_divider(n))

        # Capital
        print(_row("Totalt investert", *[_nok(s.capital_split.total_cost) for s in summaries]))
        print(_row("  - Lån", *[_nok(s.capital_split.total_borrowed) for s in summaries]))
        print(_row("  - Egenkapital (innskutt)", *[_nok(s.capital_split.total_equity) for s in summaries]))
        print(_divider(n))

        # Value & borrowed
        print(_row("Markedsverdi", *[_nok(s.current_value) for s in summaries]))
        print(_row("Utestående lån", *[_nok(s.current_value - s.net_equity_value) for s in summaries]))
        print(_row("Netto egenkapitalverdi", *[_nok(s.net_equity_value) for s in summaries]))
        print(_divider(n))

        # Dividends & interest
        print(_row("Reinvestert utbytte", *[_nok(s.total_dividend_reinvested) for s in summaries]))
        print(_row("Betalt rente (totalt)", *[_nok(s.total_interest_paid) for s in summaries]))
        print(_divider(n))

        # Profit / loss
        print(_row("Gevinst/tap (brutto)", *[_nok(s.profit_loss_gross) for s in summaries]))
        print(_row("Gevinst/tap (netto)", *[_nok(s.profit_loss_net) for s in summaries]))
        print(_divider(n))

        # Returns
        print(_row("ROA (brutto, % av kost)", *[_pct(s.returns.return_on_total_assets_pct) for s in summaries]))
        print(_row("ROE (netto, % av innskutt+rente)", *[_pct(s.returns.return_on_equity_net_pct) for s in summaries]))
        print(_row("ROE annualisert", *[_pct(s.returns.annualized_return_on_equity_pct) for s in summaries]))
        print(_divider(n))

        # Borrowing costs
        print(_row("Månedlig rentekostnad (nå)", *[_nok(s.borrowing_costs.monthly_current) for s in summaries]))
        print(_row("Årlig rentekostnad (nå)", *[_nok(s.borrowing_costs.annual_current) for s in summaries]))
        print(_divider(n))

        # Portfolio totals
        total_cost = sum((s.capital_split.total_cost for s in summaries), DECIMAL_ZERO)
        total_borrowed = sum((s.capital_split.total_borrowed for s in summaries), DECIMAL_ZERO)
        total_equity_in = sum((s.capital_split.total_equity for s in summaries), DECIMAL_ZERO)
        total_value = sum((s.current_value for s in summaries), DECIMAL_ZERO)
        total_outstanding = sum((s.current_value - s.net_equity_value for s in summaries), DECIMAL_ZERO)
        total_net_equity = sum((s.net_equity_value for s in summaries), DECIMAL_ZERO)
        total_dividends = sum((s.total_dividend_reinvested for s in summaries), DECIMAL_ZERO)
        total_interest = sum((s.total_interest_paid for s in summaries), DECIMAL_ZERO)
        total_gross_pl = sum((s.profit_loss_gross for s in summaries), DECIMAL_ZERO)
        total_net_pl = sum((s.profit_loss_net for s in summaries), DECIMAL_ZERO)
        total_monthly = sum((s.borrowing_costs.monthly_current for s in summaries), DECIMAL_ZERO)
        total_annual = sum((s.borrowing_costs.annual_current for s in summaries), DECIMAL_ZERO)

        effective_eq = total_equity_in + total_interest
        roa_total = (total_gross_pl / total_cost * 100) if total_cost else None
        roe_total = (total_net_pl / effective_eq * 100) if effective_eq else None

        print()
        print("=" * (30 + COL_WIDTH * n))
        print("  PORTEFØLJE TOTAL")
        print("=" * (30 + COL_WIDTH * n))
        print(f"  {'Totalt investert':<32} {_nok(total_cost):>20}")
        print(f"  {'  - Lån':<32} {_nok(total_borrowed):>20}")
        print(f"  {'  - Egenkapital (innskutt)':<32} {_nok(total_equity_in):>20}")
        print(f"  {'Markedsverdi':<32} {_nok(total_value):>20}")
        print(f"  {'Utestående lån':<32} {_nok(total_outstanding):>20}")
        print(f"  {'Netto egenkapitalverdi':<32} {_nok(total_net_equity):>20}")
        print(f"  {'Reinvestert utbytte':<32} {_nok(total_dividends):>20}")
        print(f"  {'Betalt rente':<32} {_nok(total_interest):>20}")
        print(f"  {'Gevinst/tap (brutto)':<32} {_nok(total_gross_pl):>20}")
        print(f"  {'Gevinst/tap (netto)':<32} {_nok(total_net_pl):>20}")
        print(f"  {'ROA (brutto)':<32} {_pct(roa_total):>20}")
        print(f"  {'ROE (netto)':<32} {_pct(roe_total):>20}")
        print(f"  {'Månedlig rentekostnad (nå)':<32} {_nok(total_monthly):>20}")
        print(f"  {'Årlig rentekostnad (nå)':<32} {_nok(total_annual):>20}")
        print("=" * (30 + COL_WIDTH * n))
        print()


if __name__ == "__main__":
    main()
