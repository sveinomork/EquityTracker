from __future__ import annotations

from app.scripts.import_dividend_distributions import main as import_dividends_main
from app.scripts.import_loan_rates_seed import main as import_loan_rates_main
from app.scripts.import_transactions_seed import main as import_transactions_main


def main() -> None:
    """Run all seed scripts in the expected execution order."""
    print("Seeding transactions...")
    import_transactions_main()
    print("Seeding loan rates...")
    import_loan_rates_main()
    print("Seeding dividend distributions...")
    import_dividends_main()
    print("Seeding complete.")


if __name__ == "__main__":
    main()
