# Multi-currency Dashboard Design

- **Task ID:** G1-11
- **Date:** 2026-07-25
- **Status:** Proposed design — documentation only. No formulas, sheets, or
  the PM OS workbook were modified, per instruction.
- **Builds on:** `SPEC_G1-09_Onboarding_Data_Model.md`, which first surfaced
  this bug while specifying onboarding fields. This document is the
  detailed follow-up it named as Backlog item 7.

## 1. KPI impact analysis

Reviewed every formula in `00_Dashboard`, `Cost_Model`, and `05_KPI` in the
current PM OS workbook directly (cell-by-cell, not from memory) to
determine which assume a single currency.

### 1.1 Affected — assumes ¥2,980 / single currency

| # | Cell | KPI | Formula | Problem |
|---|---|---|---|---|
| 1 | `00_Dashboard!B12` | MRR | `=B10*2980` | Hardcodes ¥2,980 × contract **count**. A USD customer is counted the same as a JPY customer |
| 2 | `00_Dashboard!B26` (exec summary "Revenue"/"MRR") | Revenue, MRR | `=B12` | Inherits #1 directly |
| 3 | `Cost_Model!B17` | MRR (mirror calc) | `=B4*B5` | Same bug — `B4` (単価) is a single ¥2,980 input, `B5` is total customer count |
| 4 | `Cost_Model!B18` | 決済手数料 (payment fee) | `=B17*B6` | Inherits #3's currency error, **and** Stripe's fee rate/structure typically differs by currency/region — `B6` (3.6%) is a single rate assumed for all transactions |
| 5 | `Cost_Model!D4:D7` | 月次粗利 per customer-count scenario (10/30/100/300) | `=D{r}*$B$4 - ...` (4 formulas) | All four reference `$B$4` (2980) directly |
| 6 | `Cost_Model!B22` | 総コスト | `=B7+B8+B9+B18+B19+B21` | Mixes JPY-denominated fixed costs (固定費/月, AI費, メール費 — all entered as plain JPY numbers) with variable costs derived from #3's broken revenue figure — a **second, distinct** currency problem (cost-revenue currency mismatch), not just the price hardcode |
| 7 | `Cost_Model!B23` | 月次粗利 (gross profit) | `=B17-B22` | Propagates #3 and #6 |
| 8 | `Cost_Model!B24` | 粗利率 (gross margin %) | `=B23/B17` | A ratio, but built on broken absolute values — the *percentage* itself becomes unreliable, not just currency-labeled wrong |
| 9 | `Cost_Model!B25` | 想定LTV | `=B4/B13` | Single-currency unit price ÷ churn rate |
| 10 | `Cost_Model!B26` | CAC許容上限 | `=B4*3*B24` | Compounds #9's and #8's errors |
| 11 | `05_KPI!M4` | CAC上限(参考) | `=Cost_Model!B26` | Inherits #10 |
| 12 | `05_KPI!M5` | 想定LTV(参考) | `=Cost_Model!B25` | Inherits #9 |

**12 distinct formulas/formula groups affected**, all downstream of two root
causes: (a) `00_Dashboard!B12` and `Cost_Model!B4`/`B17` treating "customer
count × one price" as MRR, and (b) `Cost_Model`'s cost side never having a
currency dimension to begin with.

### 1.2 Not affected — currency-safe as-is

| KPI | Cell(s) | Why safe |
|---|---|---|
| Active Contracts (契約数) | `00_Dashboard!B10`, `Cost_Model!B5` | Plain count, no amount involved |
| 返信率 / 契約率 (reply rate / close rate) | `00_Dashboard!B8/B11`, `05_KPI!D:D`/`G:G` | Ratios of counts (replies÷sends, contracts÷sends) — currency never enters the calculation |
| 月次解約率 (churn rate) | `00_Dashboard!B14` | A percentage of customer count, not revenue |
| 診断店舗数 / 送信数 / 返信数 / 商談数 / 自動化タスク数 / 法務未完了件数 | Various `00_Dashboard` rows | All plain counts |

### 1.3 Not yet implemented, but named in this task — how they'd be affected if added

- **ARR** — doesn't exist as a formula today. If added as `MRR×12`, it
  would inherit every issue above unless built on the corrected model from
  §2 onward.
- **Average Revenue** (per customer) — doesn't exist as a named formula
  today (conceptually `Cost_Model!B4`, the flat unit price). Same
  single-currency assumption as MRR.
- **Revenue Trend** — no time-series revenue KPI exists yet (`05_KPI` tracks
  send/reply/contract counts weekly, not revenue). Should be built
  currency-aware from the start rather than retrofitted — see §4.

## 2. Currency-safe data model

Proposed fields (additive — extends `SPEC_G1-09_Onboarding_Data_Model.md`,
which specified `Currency` per customer but **did not** specify a separate
Billing Amount field; that gap is closed here):

| Field | Scope | Type | Purpose |
|---|---|---|---|
| **Currency (通貨)** | Per customer (`Customers` row) | Enum, ISO 4217 (`JPY`, `USD`) | Already specified in `SPEC_G1-09`. What currency this customer is actually billed in |
| **Billing Amount (請求金額)** | Per customer (`Customers` row) | Number | **New — not in `SPEC_G1-09`, added here.** The actual amount billed, in `Currency`'s units (e.g. `2980` for a JPY plan, `19.99` for a USD plan). MRR must be computed by summing this field grouped by Currency, never by `count × one hardcoded price` |
| **Local Currency (現地通貨)** | Same as Currency | — | Not a separate field — "Local Currency" and "Currency" are the same concept in this model; listed separately in the task instructions but there's no reason to duplicate the field |
| **Reporting Currency (レポート通貨)** | Single value, business-wide (e.g. a `Settings` row) | Enum, ISO 4217 | The currency aggregate/consolidated KPIs are converted *to* for executive display. Recommended: `JPY`, since the business is Japan-headquartered (domain/DNS/Workspace all JPY-billed contexts per `Architecture.md`'s asset inventory) |
| **Exchange Rate (為替レート)** | A small reference table, **not** a per-customer field | Table: Date, From, To, Rate | Rates fluctuate daily — storing a rate on each customer row would go stale and conflate "rate at signup" with "rate for today's report." Keep as a separate, small `FX_Rates`-style table (or even a single formula cell) instead |

**Concrete, low-maintenance option for the FX rate:** Google Sheets has a
native `GOOGLEFINANCE("CURRENCY:USDJPY")` function — a live rate with zero
external API/credential setup, fitting this project's stated "low
maintenance, low cost" priority better than any custom integration. A
single reference cell (e.g. `Settings!為替レート(USD→JPY)`) refreshed live
by this formula is sufficient at this scale; a full historical-rate table
is not recommended unless/until per-transaction accounting-grade FX
tracking is actually required (a question for accounting, not engineering
— see Risks).

**Recommended additive change to `SPEC_G1-09`'s field list:** add `Billing
Amount (請求金額)` as a required new field alongside `Currency` — both are
needed together; `Currency` alone cannot fix the MRR calculation.

## 3. Separate totals vs. converted base currency — recommendation

### Option 1: Separate JP / US totals only

- **Pros:** No FX risk in the reported figures — a JPY MRR figure never
  moves because of exchange-rate noise, only because of actual business
  change. Matches how revenue is typically recognized for accounting/tax
  purposes (in the currency actually billed). Simple `SUMIFS` by Currency,
  no external data dependency.
- **Cons:** No single "total MRR" number for at-a-glance executive
  reporting — the PM OS's own `00_Dashboard` is explicitly designed for
  quick health checks, and "check two numbers instead of one" works against
  that.

### Option 2: Converted to a single base (reporting) currency

- **Pros:** One consolidated MRR/ARR figure, matching the executive-summary
  intent of `00_Dashboard`.
- **Cons:** Reported revenue would fluctuate with exchange rates, not just
  business performance — a well-known distortion in multi-currency SaaS
  reporting. Requires deciding *which* rate (today's spot rate? a period
  average? the rate at each transaction's original billing date?) —
  different choices give different answers, and picking one implicitly is
  worse than stating the choice explicitly. Adds a live external data
  dependency (`GOOGLEFINANCE`), which, while low-maintenance, can still be
  unavailable or delayed.

### Recommendation: both, clearly labeled — not a forced choice

Keep **separate, authoritative per-currency totals** as the source of
truth (accurate, no FX noise, suitable for accounting), and add **one
converted, clearly-labeled consolidated figure** (e.g. "MRR (JPY-equivalent,
spot rate as of {date})") purely for at-a-glance executive visibility. This
mirrors the PM OS's existing summary/detail split (`00_Dashboard` = quick
view referencing `05_KPI`/`Cost_Model` for detail) — the converted total
belongs in the summary layer, with the authoritative per-currency numbers
staying in the detail sheets underneath it. Label the converted figure
explicitly as a spot-rate estimate so it is never mistaken for an
accounting-grade consolidated revenue number.

## 4. Migration plan (documentation only — no formulas changed by this task)

1. Add `Currency` + `Billing Amount` columns to `Customers` (extends the
   `SPEC_G1-09` column additions — same authorization gate, same Task ID
   family).
2. Add a Plan × Currency → Price reference table to `Settings`, replacing
   the implicit "price is always ¥2,980" assumption baked into formulas
   today. Price changes then become a data edit, not a formula edit.
3. Add a live FX reference cell (`GOOGLEFINANCE`-based) to `Settings`.
4. Rewrite `00_Dashboard!B12`'s MRR formula to sum `Customers!請求金額`
   grouped by `Currency` (e.g. separate JPY-MRR / USD-MRR `SUMIFS`
   formulas) instead of `count × 2980`.
5. Add the converted consolidated MRR row per §3's recommendation, with an
   explicit "as of {date}, spot rate" label.
6. Rebuild `Cost_Model` per-currency: separate the JPY-cost-basis
   (`固定費/月`, `AI費`, `メール費` — all currently plain JPY numbers) from
   any USD-side costs, and stop deriving `決済手数料` from a single
   assumed rate if Stripe's actual JPY vs. USD fee structure differs
   (verify with Stripe, don't assume).
7. Add ARR (`= MRR × 12`, per-currency and consolidated) if wanted, built
   on the corrected model — not before.
8. Add Revenue Trend as new `05_KPI` columns from the start of this work,
   split by currency, rather than retrofitting a time series later.
9. **Validate with a synthetic (test) USD customer row before any real US
   customer is onboarded** — this is the concrete gate that should block
   onboarding the first real US customer, independent of the rest of the
   onboarding-page work in `SPEC_G1-09`/`ADD_G1-06D`.

Every step above needs its own Task ID and explicit authorization before
implementation — none are done by this task.

## 5. Risk assessment

| Risk | Severity | Notes |
|---|---|---|
| **First real USD customer silently corrupts MRR today** | High, immediate | Already flagged in `SPEC_G1-09`/`Decision_Log.md`; not hypothetical — a US Payment Link already exists (G1-06) |
| FX volatility distorting the converted consolidated figure | Medium | Mitigated by clear labeling (§3) — a design choice, not eliminable |
| FX rate staleness if the live-rate approach isn't actually refreshed/viewed | Low–Medium | `GOOGLEFINANCE` refreshes automatically on sheet view/recalc, but only when the sheet is open — a rate could be stale on a report generated from a cached/offline export |
| Stripe fee-rate mismatch between JPY and USD transactions | Medium | `Cost_Model!B6` (3.6%) is a single assumed rate; needs verification against Stripe's actual per-currency fee schedule, not assumed equal |
| Tax/accounting treatment of multi-currency revenue | Unknown — flagged, not assessed | Outside engineering scope, same category as `SPEC_G1-09`'s flagged need for legal review of non-JP consent requirements. Recommend accounting/legal input before real USD revenue is recognized in any reporting used externally |
| Added complexity (FX table, per-currency formulas) increasing formula-error surface | Low–Medium | Mitigated by keeping the design as simple as possible (§3's recommendation deliberately avoids per-transaction historical-rate accounting unless proven necessary) |

## 6. Cross-references

- `SPEC_G1-09_Onboarding_Data_Model.md` — where `Currency` was first
  proposed as a customer field (this document adds `Billing Amount`
  alongside it) and where this MRR bug was first surfaced (§ Gap 4).
- `ADD_G1-06D_Onboarding_Data_Bridge.md` — the data-bridge mechanism these
  new fields would flow through.
- `Decision_Log.md` — G1-06 (JP+US Payment Links confirmed, the evidence
  basis for all multi-currency work).
