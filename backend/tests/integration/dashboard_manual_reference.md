# Dashboard manual reference scenario (2 funds)

This document defines a small, deterministic scenario used to verify dashboard numbers with manual calculations.

## Scope

We validate only:

- 90d (from performance windows, price based)
- 24m (cashflow-adjusted period metric)
- Total (cashflow-adjusted total metric)

We also include interest effects (after-interest values) so both gross and net-of-interest dashboard values can be checked.

As-of date: 2026-01-01
24m start date: 2024-01-02 (730 days back)
90d reference date: 2025-10-03

## Input data

### Fund 1: FHY (distributing)

Transactions:

- 2024-01-02 BUY: units=100, total=10000, borrowed=4000
- 2025-11-01 BUY: units=50, total=4700, borrowed=0
- 2025-12-15 DIVIDEND_REINVEST on lot 1: units=10, total=900
- 2025-12-20 SELL on lot 1: units=20, total=1900

Prices:

- 2024-01-02: 100
- 2025-10-03: 92
- 2026-01-01: 100

Loan rates:

- 2024-01-01: nominal_rate=10.0 (10 percent)

Derived units:

- units at 24m start (2024-01-02): 100
- units at end (2026-01-01): 100 + 50 + 10 - 20 = 140

### Fund 2: KNB (accumulating)

Transactions:

- 2024-01-02 BUY: units=200, total=10000, borrowed=0
- 2025-06-01 SELL on lot 1: units=50, total=2900
- 2025-11-15 BUY: units=40, total=2400, borrowed=0

Prices:

- 2024-01-02: 50
- 2025-10-03: 59
- 2026-01-01: 62

Derived units:

- units at 24m start (2024-01-02): 200
- units at end (2026-01-01): 200 - 50 + 40 = 190

## Manual calculations

Notation:

- value_t0 = units_t0 \* start_price
- value_t1 = units_t1 \* end_price
- net_external_cashflow = sum(BUY in (start, end]) - sum(SELL in (start, end])
- gross_24m = (value_t1 - value_t0) - net_external_cashflow
- base_24m = value_t0 + net_external_cashflow
- gross_pct = gross / base \* 100
- total_gross = value_t1 - total_buy_cost
- total_base = total_buy_cost

### 90d (price-only window)

FHY:

- (100 / 92 - 1) \* 100 = 8.6956521739

KNB:

- (62 / 59 - 1) \* 100 = 5.0847457627

### FHY 24m

- value_t0 = 100 \* 100 = 10000
- value_t1 = 140 \* 100 = 14000
- net_external_cashflow = 4700 - 1900 = 2800
- gross_24m = (14000 - 10000) - 2800 = 1200
- base_24m = 10000 + 2800 = 12800
- gross_pct_24m = 1200 / 12800 \* 100 = 9.375

### FHY interest (24m and Total in this scenario)

Interest logic uses daily simple accrual with day basis 365.

Borrowed balance path:

- 4000 until sell adjustment date
- sell 20 units out of original 100 => borrowed reduction 20% = 800
- new borrowed balance from 2025-12-20 onward = 3200

Day counts for period 2024-01-03..2026-01-01:

- 2024-01-03..2025-12-19: 717 days at 4000
- 2025-12-20..2026-01-01: 13 days at 3200

Interest:

- 4000 _ 0.10 / 365 _ 717 + 3200 _ 0.10 / 365 _ 13
- = 797.1506849315

After-interest FHY 24m:

- 1200 - 797.1506849315 = 402.8493150685
- after_interest_pct_24m = 402.8493150685 / 12800 \* 100 = 3.1472602739

### FHY Total

- total_buy_cost = 10000 + 4700 = 14700
- total_gross = 14000 - 14700 = -700
- total_base = 14700
- gross_pct_total = -700 / 14700 \* 100 = -4.7619047619
- after_interest_total = -700 - 797.1506849315 = -1497.1506849315
- after_interest_pct_total = -1497.1506849315 / 14700 \* 100 = -10.1846985370

### KNB 24m

- value_t0 = 200 \* 50 = 10000
- value_t1 = 190 \* 62 = 11780
- net_external_cashflow = 2400 - 2900 = -500
- gross_24m = (11780 - 10000) - (-500) = 2280
- base_24m = 10000 - 500 = 9500
- gross_pct_24m = 2280 / 9500 \* 100 = 24.0
- after-interest values are same as gross (no borrowing)

### KNB Total

- total_buy_cost = 10000 + 2400 = 12400
- total_gross = 11780 - 12400 = -620
- total_base = 12400
- gross_pct_total = -620 / 12400 \* 100 = -5.0
- after-interest values are same as gross

### Portfolio 24m (sum of fund period entries)

- gross_24m = 1200 + 2280 = 3480
- base_24m = 12800 + 9500 = 22300
- gross_pct_24m = 3480 / 22300 \* 100 = 15.6053811659
- after_interest_24m = 3480 - 797.1506849315 = 2682.8493150685
- after_interest_pct_24m = 2682.8493150685 / 22300 \* 100 = 12.0307144173

### Portfolio Total

- total_gross = -700 + (-620) = -1320
- total_base = 14700 + 12400 = 27100
- gross_pct_total = -1320 / 27100 \* 100 = -4.8708487085
- after_interest_total = -1320 - 797.1506849315 = -2117.1506849315
- after_interest_pct_total = -2117.1506849315 / 27100 \* 100 = -7.8123641510

## Expected checks in test

- FHY performance_windows[90d_pct] ~= 8.6956521739
- KNB performance_windows[90d_pct] ~= 5.0847457627
- 24m and Total gross/after-interest amounts and percentages for FHY, KNB, and portfolio summary match formulas above
- Allowed numeric tolerance: absolute 0.01
