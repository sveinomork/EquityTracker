# EquityTracker API-dokumentasjon

Denne dokumentasjonen dekker hele backend-API-et i prosjektet per nåværende implementasjon.

## Base URL og versjon

- Lokal app: `http://localhost:8000`
- API-prefix: `/api/v1`
- Full base for API-kall: `http://localhost:8000/api/v1`

Eksempel:

```bash
curl http://localhost:8000/api/v1/funds
```

## Interaktiv API-dokumentasjon (OpenAPI)

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Innhold

1. Generelt
2. Feilhåndtering
3. Datatyper og konvensjoner
4. Endepunkter
5. Analyseobjekter (summary/historikk)
6. Eksempel-flyt

## 1. Generelt

- Ingen autentisering er implementert per nå.
- Alle datoer bruker format `YYYY-MM-DD`.
- UUID brukes som ID for fond, transaksjoner, priser og renter.
- Decimal-felt serialiseres som JSON-tall (float).

## 2. Feilhåndtering

API-et bruker standard FastAPI-validering + domenefeil.

- `404 Not Found`
  - `{"detail": "Fund not found"}`
  - `{"detail": "Transaction not found"}`
- `400 Bad Request`
  - Domenevalidering, f.eks. ugyldig lot-referanse eller borrowed_amount > total_amount.
- `422 Unprocessable Entity`
  - Pydantic/FastAPI valideringsfeil (manglende felt, feil datatype, out-of-range).

## 3. Datatyper og konvensjoner

### TransactionType

- `BUY`
- `SELL`
- `DIVIDEND_REINVEST`

### Viktige regler

- `SELL` lagres med negative `units`.
- `DIVIDEND_REINVEST` må ha `lot_id`.
- `BUY` kan ikke ha `lot_id`.
- `borrowed_amount` kan ikke overstige `total_amount`.
- Hvis `SELL` opprettes uten `lot_id`, brukes FIFO-splitting automatisk på tilgjengelige lots.

## 4. Endepunkter

### 4.1 Health

#### GET `/health`

Brukes for enkel healthcheck uten API-prefix.

Respons:

```json
{
  "status": "ok"
}
```

### 4.2 Funds

#### POST `/api/v1/funds`

Opprett nytt fond.

Request body:

```json
{
  "name": "Heimdal Høyrente",
  "ticker": "HHR",
  "is_distributing": true,
  "manual_taxable_gain_override": 0
}
```

Felt:

- `name` string, 1..255
- `ticker` string, 1..32 (normaliseres til uppercase)
- `is_distributing` bool (default `false`)
- `manual_taxable_gain_override` number >= 0 eller `null`

Respons (`201 Created`): `FundRead`

```json
{
  "id": "uuid",
  "name": "Heimdal Høyrente",
  "ticker": "HHR",
  "is_distributing": true,
  "manual_taxable_gain_override": 0
}
```

#### GET `/api/v1/funds`

Lister alle fond.

Respons: `FundRead[]`

#### PATCH `/api/v1/funds/{fund_id}/tax-config`

Oppdater skattekonfig på fond.

Path params:

- `fund_id` UUID

Request body:

```json
{
  "is_distributing": true,
  "manual_taxable_gain_override": 0
}
```

Alle felt er valgfrie.

Respons: `FundRead`

#### GET `/api/v1/funds/{fund_id}/summary`

Henter komplett analyse per fond.

Query params:

- `as_of_date` (optional, `YYYY-MM-DD`)

Respons: `FundSummary`

Inneholder blant annet:

- `capital_split`
- `current_value`, `net_equity_value`
- `total_interest_paid`
- `realized_profit_from_sold_positions`
- `profit_loss_gross`, `profit_loss_gross_including_realized`, `profit_loss_net`
- `returns`
- `performance_windows`
- `period_metrics` (`1d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `YTD`, `12m`, `24m`, `Total`)
- `tax_summary`
- `true_net_worth`

#### GET `/api/v1/funds/{fund_id}/lots`

Henter lot-basert analyse for fondet.

Query params:

- `as_of_date` (optional)

Respons: `FundLotsSummary`

Inneholder:

- `market_price_per_unit`, `market_price_date`
- `lots[]` med `LotSummary` per kjøpslot

### 4.3 Transactions

#### POST `/api/v1/transactions`

Opprett transaksjon.

Request body:

```json
{
  "fund_id": "uuid",
  "lot_id": null,
  "date": "2026-05-08",
  "type": "BUY",
  "units": 100,
  "price_per_unit": 102.34,
  "total_amount": 10234,
  "borrowed_amount": 5000
}
```

Validering:

- `units > 0` i input (service setter `SELL` til negative units internt)
- `price_per_unit > 0`
- `total_amount > 0`
- `borrowed_amount >= 0`
- `borrowed_amount <= total_amount`
- `DIVIDEND_REINVEST` krever `lot_id`

Spesialregler:

- `SELL` uten `lot_id` trigges som FIFO-salg over tilgjengelige BUY-lots.

Respons (`201`): `TransactionRead`

#### PATCH `/api/v1/transactions/{transaction_id}`

Delvis oppdatering av transaksjon.

Path params:

- `transaction_id` UUID

Request body (alle felt valgfrie):

```json
{
  "date": "2026-05-08",
  "type": "SELL",
  "units": 50,
  "price_per_unit": 103,
  "total_amount": 5150,
  "borrowed_amount": 2000,
  "lot_id": "uuid"
}
```

Respons: `TransactionRead`

#### GET `/api/v1/transactions`

Lister transaksjoner.

Query params:

- `fund_id` UUID (optional)

Respons: `TransactionRead[]`

### 4.4 Prices

#### POST `/api/v1/funds/{fund_id}/prices`

Batch upsert av dagspriser.

Path params:

- `fund_id` UUID

Request body:

```json
{
  "items": [
    { "date": "2026-05-07", "price": 101.23 },
    { "date": "2026-05-08", "price": 101.57 }
  ]
}
```

Validering:

- Hver `price > 0`

Respons (`201`): `DailyFundPriceRead[]`

#### GET `/api/v1/funds/{fund_id}/prices`

Lister priser for fond.

Query params:

- `from_date` optional
- `to_date` optional
- `limit` optional (`1..5000`)

Respons: `DailyFundPriceRead[]`

### 4.5 Rates

#### POST `/api/v1/funds/{fund_id}/rates`

Batch upsert av lånerenter.

Path params:

- `fund_id` UUID

Request body:

```json
{
  "items": [
    { "effective_date": "2026-01-01", "nominal_rate": 6.75 },
    { "effective_date": "2026-04-01", "nominal_rate": 6.95 }
  ]
}
```

Validering:

- `nominal_rate > 0`

Respons (`201`): `LoanRateRead[]`

#### GET `/api/v1/funds/{fund_id}/rates`

Lister renter for fond.

Query params:

- `from_date` optional
- `to_date` optional
- `limit` optional (`1..5000`)

Respons: `LoanRateRead[]`

### 4.6 Portfolio

#### GET `/api/v1/portfolio/summary`

Henter porteføljesammendrag på tvers av alle fond.

Query params:

- `as_of_date` optional

Respons: `PortfolioSummary`

Inneholder:

- `as_of_date`
- `funds[]` (`FundSummary` per fond)
- `totals` (`PortfolioTotals`)
- `period_metrics` (`PeriodMetricsByWindow`)

#### GET `/api/v1/portfolio/history`

Henter månedlige snapshots for totalporteføljen.

Query params:

- `as_of_date` optional

Respons: `PortfolioHistoryPoint[]`

Felter per punkt:

- `date`
- `market_value`
- `total_equity`
- `total_borrowed`
- `total_interest_paid`
- `net_value`

Merknad:

- For fordelende fond behandles reinvesterte utbytter i historikk med effekt fra første handledag i året.

#### GET `/api/v1/portfolio/reconciliation/fund-period`

Diagnostikk-endepunkt for perioderegnskap per fond.

Query params:

- `ticker` optional, default `FHY`
- `as_of_date` optional

Respons: `FundPeriodReconciliation`

Inneholder `rows[]` med beregningsgrunnlag per periode.

### 4.7 Sync

#### POST `/api/v1/sync/yahoo`

Trigger Yahoo Finance-sync for alle kjente tickere i systemet.

Query params:

- `start_date` optional (default internt: `2023-01-01`)

Respons: `SyncResult[]`

Eksempel:

```json
[
  { "ticker": "HHR", "upserted": 650, "error": null },
  { "ticker": "FHY", "upserted": 650, "error": null }
]
```

## 5. Analyseobjekter (summary/historikk)

Denne seksjonen beskriver de viktigste strukturerte response-objektene.

### 5.1 FundSummary

Kjerneobjekt for fondsanalyse.

Nøkkelfelter:

- Identitet: `fund_id`, `fund_name`, `ticker`, `as_of_date`
- Kapital: `capital_split` (`total_cost`, `total_equity`, `total_borrowed`)
- Verdi: `current_value`, `net_equity_value`
- Kost/PNL: `total_interest_paid`, `realized_profit_from_sold_positions`,
  `profit_loss_gross`, `profit_loss_gross_including_realized`, `profit_loss_net`
- Avkastning: `returns`, `performance_windows`, `total_return`, `period_metrics`
- Skatt: `tax_summary`, `true_net_worth`

### 5.2 PeriodMetricsByWindow

Brukes både på fonds- og porteføljenivå.

JSON-nøkler i respons:

- `1d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `YTD`, `12m`, `24m`, `Total`

Hver periode inneholder:

- Tidsrom, kapitalbase, brutto endring, rentekost, skattekreditt,
  løpende utbytteskatt, netto marginer og split-metrics (`gross_*`, `after_interest_*`).

### 5.3 PortfolioTotals

Summerer hele porteføljen:

- `total_cost`, `total_market_value`, `current_value`
- `net_equity_value`
- `total_interest_paid`
- `total_equity`, `total_borrowed`
- `profit_loss_net`
- `weighted_average_days_invested`
- `weighted_annualized_return_on_cost_pct`
- `total_return`
- `true_net_worth_nok`, `true_net_worth`

## 6. Eksempel-flyt

Typisk sekvens for ny portefølje:

1. Opprett fond via `POST /api/v1/funds`
2. Legg inn renter via `POST /api/v1/funds/{fund_id}/rates`
3. Legg inn priser via `POST /api/v1/funds/{fund_id}/prices`
4. Registrer transaksjoner via `POST /api/v1/transactions`
5. Hent analyser:
   - `GET /api/v1/funds/{fund_id}/summary`
   - `GET /api/v1/funds/{fund_id}/lots`
   - `GET /api/v1/portfolio/summary`
   - `GET /api/v1/portfolio/history`

## cURL-snutter

Opprett fond:

```bash
curl -X POST "http://localhost:8000/api/v1/funds" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Heimdal Høyrente",
    "ticker": "HHR",
    "is_distributing": true
  }'
```

List transaksjoner for fond:

```bash
curl "http://localhost:8000/api/v1/transactions?fund_id=<FUND_UUID>"
```

Porteføljehistorikk:

```bash
curl "http://localhost:8000/api/v1/portfolio/history"
```
