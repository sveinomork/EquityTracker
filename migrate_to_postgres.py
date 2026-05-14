#!/usr/bin/env python3
"""
Migrate data from SQLite (backend/rentefond.db) to PostgreSQL in Docker.
"""

import sqlite3
from decimal import Decimal
from datetime import date, datetime
import sys

import psycopg

# SQLite connection
sqlite_path = "backend/rentefond.db"
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL connection
pg_conn = psycopg.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="equitytracker"
)
pg_cursor = pg_conn.cursor()

def migrate_funds():
    """Copy funds from SQLite to PostgreSQL."""
    print("Migrating funds...")
    sqlite_cursor.execute("SELECT id, name, ticker, is_distributing, manual_taxable_gain_override, created_at, updated_at FROM funds")
    rows = sqlite_cursor.fetchall()
    
    for row in rows:
        pg_cursor.execute("""
            INSERT INTO funds (id, name, ticker, is_distributing, manual_taxable_gain_override, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            row["id"],
            row["name"],
            row["ticker"],
            bool(row["is_distributing"]) if row["is_distributing"] is not None else False,
            row["manual_taxable_gain_override"],
            row["created_at"],
            row["updated_at"]
        ))
    
    pg_conn.commit()
    print(f"  ✓ Migrated {len(rows)} funds")

def migrate_transactions():
    """Copy transactions from SQLite to PostgreSQL."""
    print("Migrating transactions...")
    sqlite_cursor.execute("""
        SELECT id, fund_id, lot_id, date, type, units, price_per_unit, total_amount, borrowed_amount, equity_amount, created_at, updated_at 
        FROM transactions
    """)
    rows = sqlite_cursor.fetchall()
    
    for row in rows:
        pg_cursor.execute("""
            INSERT INTO transactions 
            (id, fund_id, lot_id, date, type, units, price_per_unit, total_amount, borrowed_amount, equity_amount, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            row["id"],
            row["fund_id"],
            row["lot_id"],
            row["date"],
            row["type"],
            Decimal(str(row["units"])),
            Decimal(str(row["price_per_unit"])),
            Decimal(str(row["total_amount"])),
            Decimal(str(row["borrowed_amount"])),
            Decimal(str(row["equity_amount"])),
            row["created_at"],
            row["updated_at"]
        ))
    
    pg_conn.commit()
    print(f"  ✓ Migrated {len(rows)} transactions")

def migrate_prices():
    """Copy daily fund prices from SQLite to PostgreSQL."""
    print("Migrating daily fund prices...")
    sqlite_cursor.execute("""
        SELECT id, fund_id, date, price, created_at, updated_at 
        FROM daily_fund_prices
    """)
    rows = sqlite_cursor.fetchall()
    
    for row in rows:
        pg_cursor.execute("""
            INSERT INTO daily_fund_prices (id, fund_id, date, price, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (fund_id, date) DO NOTHING
        """, (
            row["id"],
            row["fund_id"],
            row["date"],
            Decimal(str(row["price"])),
            row["created_at"],
            row["updated_at"]
        ))
    
    pg_conn.commit()
    print(f"  ✓ Migrated {len(rows)} prices")

def migrate_rates():
    """Copy loan rate history from SQLite to PostgreSQL."""
    print("Migrating loan rate history...")
    sqlite_cursor.execute("""
        SELECT id, fund_id, effective_date, nominal_rate, created_at, updated_at 
        FROM loan_rate_history
    """)
    rows = sqlite_cursor.fetchall()
    
    for row in rows:
        pg_cursor.execute("""
            INSERT INTO loan_rate_history (id, fund_id, effective_date, nominal_rate, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (fund_id, effective_date) DO NOTHING
        """, (
            row["id"],
            row["fund_id"],
            row["effective_date"],
            Decimal(str(row["nominal_rate"])),
            row["created_at"],
            row["updated_at"]
        ))
    
    pg_conn.commit()
    print(f"  ✓ Migrated {len(rows)} rates")

if __name__ == "__main__":
    try:
        print(f"Starting migration from {sqlite_path} to PostgreSQL...\n")
        migrate_funds()
        migrate_transactions()
        migrate_prices()
        migrate_rates()
        print("\n✓ Migration completed successfully!")
        sqlite_conn.close()
        pg_conn.close()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}", file=sys.stderr)
        sqlite_conn.close()
        pg_conn.close()
        sys.exit(1)
