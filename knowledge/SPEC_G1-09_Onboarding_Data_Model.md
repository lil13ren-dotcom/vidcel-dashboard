# Production Onboarding Specification

- **Task ID:** G1-09
- **Date:** 2026-07-25
- **Status:** Proposed specification — documentation only, nothing
  implemented. No Stripe, Apps Script, or Google Sheets changes were made.
- **Builds on:** `ADD_G1-06D_Onboarding_Data_Bridge.md` (the *how* data
  reaches Google Sheets); this document defines the *what* — the field set.

## Method

All "existing" fields below are taken directly from the current Google
Form's response header (`フォームの回答 1` sheet) and the `Customers` sheet
schema in `店舗IT担当_オンボーディング管理_v1`, inspected directly during
G1-06/PM-003 (not assumed from memory or the example list in this task's
instructions). New fields are proposed **only** where there is a specific,
cited reason — per instruction, nothing is invented without justification.

**The justification for the new fields below:** G1-06 confirmed the project
owner created **both a Japan and a US Stripe Payment Link**. The current
system (Form fields, Apps Script templates, and — critically — the PM OS's
own MRR formula, `=契約数*2980` in ¥) is built Japan-only, single-currency,
single-language. Multi-market intent is now evidenced, not assumed, so
fields needed to support it are justified; fields with no such evidence are
not proposed.

## 1. Onboarding data model

### 1.1 Reused fields (already exist in the current Form + `Customers` sheet)

| Field | Required? | Type | Validation | Destination column | In current Apps Script workflow? |
|---|---|---|---|---|---|
| 店舗名 (Business Name) | Required | Text | Non-empty | `Customers!店舗名` | Yes — used in registration, task generation, emails |
| 担当者名 (Contact Person) | Required | Text | Non-empty | `Customers!担当者名` | Yes |
| メール (Email) | Required | Text | Email format | `Customers!メール` | Yes — **primary duplicate-detection key** (confirmed in `Logs`: email-match rejects re-registration) |
| 電話 (Phone) | Required (assumed) | Text | Phone format | `Customers!電話` | Yes — **secondary duplicate-detection key** (confirmed in `Logs`: phone-match rejects re-registration). Note: one test row (`UAT004`) was submitted with phone blank and was still processed, so whether the Form actually *enforces* this as required is unconfirmed — Form edit access needed to verify, not visible from spreadsheet data alone |
| LINE | Optional | Text | None observed | `Customers!LINE` | Yes. **Japan-specific messaging app — see §2 for why this becomes conditional, not obsolete, under multi-market** |
| 契約プラン (Plan) | Required | Text/Enum | Observed values: スタンダード, ベーシック | `Customers!契約プラン` | Yes |
| 契約日 (Contract Date) | Required | Date | — | `Customers!契約日` | Yes. Also observed blank in one UAT test row — may be auto-populated by Apps Script at processing time rather than customer-entered; unconfirmed |
| 備考 (Notes) | Optional | Text | None | `Customers!備考` | Yes |
| 利用規約に同意します (Terms Agreement) | Required | Checkbox | Must be checked | **`フォームの回答1` only — not copied to `Customers`** | Partially — see Gap 1 |
| プライバシーポリシーに同意します (Privacy Policy Agreement) | Required | Checkbox | Must be checked | `フォームの回答1` only | Partially — see Gap 1 |
| 特定商取引法に基づく表記を確認しました (Japan Specified Commercial Transactions Act disclosure ack) | Required for JP | Checkbox | Must be checked | `フォームの回答1` only | Partially — see Gap 1. **Japan-specific legal requirement — must become conditional on Country, see §2** |
| 月額契約・解約条件を確認しました (Monthly contract / cancellation terms ack) | Required | Checkbox | Must be checked | `フォームの回答1` only | Partially — see Gap 1 |
| 店舗住所 (Business Address) | Required (assumed) | Text | None observed | `Customers!店舗住所` | Yes. Appears absent from the earliest test rows (2026-07-08) and present from later ones (2026-07-11) — likely added to the Form partway through its life |
| 業種 (Industry) | Required (assumed) | Text | None observed | `Customers!業種` | Yes, same timing note as Address |
| 公式サイトURL (Website URL) | Optional | Text | URL format expected | `Customers!公式サイトURL` | Yes |
| GoogleビジネスプロフィールURL (GBP URL) | Optional | Text | URL format expected | `Customers!GoogleビジネスプロフィールURL` | Yes |
| InstagramURL | Optional | Text | URL format expected | `Customers!InstagramURL` | Yes |
| 支払い方法 (Payment Method) | Required | Enum | Observed values: Stripe決済, 銀行振込 | `Customers!支払い方法` | Yes |
| Stripe決済済み確認 (Stripe payment self-attestation) | Conditional (if 支払い方法=Stripe決済) | Text/Checkbox | None enforced beyond presence | `Customers!支払い状況` (derived) | Yes — **but see Gap 2: this is the customer self-reporting payment, not a verified Stripe check** |

### 1.2 New fields (not in the current Form/sheet — justified below)

| Field | Required? | Type | Validation | Destination column | Justification |
|---|---|---|---|---|---|
| Country (国) | Required | Enum (ISO 3166-1 alpha-2 recommended) | Must match a supported value | **New column in `Customers`** | JP + US Payment Links confirmed (G1-06). Drives which legal-consent set, language, and currency apply |
| Preferred Language (希望言語) | Required | Enum (`ja`, `en`) | — | **New column** | Current Form/emails are Japanese-only (confirmed: all Apps Script log messages, Settings task-template names, and email-send log entries are Japanese). US customers need English correspondence |
| Currency (通貨) | Required | Enum (`JPY`, `USD`) | Must be consistent with Country/Plan pricing | **New column** | The PM OS's own MRR formula (`00_Dashboard!B12 = 契約数*2980`, inspected directly) assumes every customer pays ¥2,980. A confirmed USD Payment Link breaks that assumption today, not hypothetically |
| WhatsApp | Optional | Text | Phone format | **New column** | LINE (existing field) is a Japan-specific app with negligible use outside Japan/Taiwan/Thailand. WhatsApp is the closest equivalent for US/international customers who won't have LINE |
| Time Zone (タイムゾーン) | Optional | Enum (IANA tz, e.g. `Asia/Tokyo`, `America/New_York`) | — | **New column** | `refreshToday`'s daily trigger runs at a fixed hour (7am, confirmed in `Logs`) with no timezone parameter observed. Needed so "today's required tasks" and support-response timing make sense for a US customer, not just implicitly JST |
| Legal Consent Set (法域別同意事項) | Required, contents conditional on Country | One or more checkboxes, set depends on Country | Must be checked for each item in the applicable set | **New column(s)**, structure TBD | The existing 特定商取引法 consent is a Japan-only legal requirement; a US customer doesn't need it but may need different disclosures. **This needs legal review, not an engineering guess** — flagged as a gap requiring input, not specified further here |

**Not proposed, deliberately:** fields like a dedicated "additional notes" beyond
the existing 備考, or anything not tied to the Country/Currency/Language
justification above. The task instruction to avoid inventing fields without
justification is taken literally — the example list in the task
("Address," "Time zone," etc.) was evaluated against actual evidence, not
copied wholesale; several of its items (Address) already exist and needed
no new field, and one (a distinct "additional notes") wasn't added because
備考 already serves that purpose.

## 2. Mapping: Vidcel Onboarding Page → Google Sheets → existing Apps Script

```
Vidcel Onboarding Page (fields in §1.1 + §1.2)
        │
        ▼  (mechanism per ADD_G1-06D: Apps Script Web App, doPost)
Google Sheets (Customers row — existing columns + new columns from §1.2)
        │
        ▼  (registration logic, decoupled from onFormSubmit per ADD_G1-06D)
Existing Apps Script workflow
  - duplicate detection (email/phone — unchanged)
  - generateInitialTasks (needs currency/language awareness — see Gap 4)
  - sendApplicationReceivedEmail / sendPaymentConfirmedEmail
    (needs language-aware templates — see Gap 4)
```

- **Reused fields (18):** all of §1.1 — the existing dedup, task-generation,
  and email logic already handles these and needs no redesign for them.
- **New fields (6):** all of §1.2 — none of these have any current Apps
  Script logic behind them yet (see Gap Analysis).
- **Obsolete / demoted fields:**
  - **LINE** — not obsolete, but becomes **conditional on Country=JP**
    rather than a universal field, with WhatsApp as its non-JP counterpart.
  - **特定商取引法 consent checkbox** — not obsolete, becomes
    **conditional on Country=JP** (part of the new Legal Consent Set).
  - **Stripe決済済み確認 (self-attestation)** — candidate for
    **eventual obsolescence** once real Stripe payment verification exists
    (see Gap 2 / G1-06). Must remain as an interim field until that
    verification is built — removing it now would remove the only signal
    the system currently has that payment happened.

## 3. Gap Analysis

1. **Legal consent isn't persisted to `Customers`.** All four consent
   checkboxes exist only in `フォームの回答1` (the raw response log), not
   in the processed `Customers` table. This is a pre-existing gap, not new —
   worth fixing regardless of the multi-market question, since it means the
   canonical customer record has no auditable consent trail today.
2. **No real Stripe payment verification exists.** `Stripe決済済み確認` is
   the customer self-reporting "I paid." Nothing in the current system
   checks against Stripe itself. This is the same gap G1-06 already
   identified as blocking Gate 1 — repeated here because it directly limits
   how much the new "Payment Method / Status" fields can be trusted.
3. **Missing Google Sheets columns:** Country, Preferred Language,
   Currency, WhatsApp, Time Zone, and a structured Legal Consent Set — none
   exist in `Customers` today. Adding columns is a small, low-risk sheet
   change, but per this task's own rule, not made here — it needs its own
   authorized Task ID.
4. **Missing Apps Script support for multi-market:**
   - `generateInitialTasks` and the email-sending functions
     (`sendApplicationReceivedEmail`, `sendPaymentConfirmedEmail`) have no
     language branching — everything observed in `Logs` and `Settings` is
     Japanese-only. A US customer today would receive Japanese task names
     and Japanese emails.
   - **`00_Dashboard!B12`'s MRR formula (`=契約数*2980`) assumes every
     customer pays ¥2,980.** A USD-paying customer breaks this silently —
     it would inflate reported MRR by treating a USD amount as if it were
     JPY. This is a real, already-existing calculation bug once a single US
     customer signs up, not a hypothetical.
   - No currency-aware or country-aware branching exists anywhere in the
     Apps Script logic inspected so far.
5. **Missing API endpoint.** Confirmed in `ADD_G1-06D_Onboarding_Data_Bridge.md`
   — the `doPost` Web App endpoint that would receive this data model
   doesn't exist yet.
6. **Missing legal review for non-Japan consent requirements.** Not an
   engineering gap — the specific text/checkboxes needed for a US customer
   is a legal question this document does not attempt to answer.
7. **No `Country`/`Currency` validation rule exists to keep Plan pricing,
   Payment Method, and Currency mutually consistent** (e.g. preventing a
   Country=US customer from being recorded with Currency=JPY). Needs to be
   specified alongside whichever validation layer implements §1.

## 4. Recommended implementation order

1. **Legal review for US (and any other non-JP) consent requirements**
   (Gap 6) — blocks finalizing the Legal Consent Set field design. Not
   Claude Code's call to make.
2. **Add the new `Customers` columns** (Country, Preferred Language,
   Currency, WhatsApp, Time Zone, structured Legal Consent) — small,
   additive sheet change. Needs its own Task ID and explicit authorization
   per this project's rules (no Apps Script/Sheets changes without one).
3. **Fix the MRR formula's currency assumption** (Gap 4) before any real
   USD customer is onboarded — otherwise `00_Dashboard` silently
   misreports revenue starting with the first US customer. This is
   independent of the onboarding page work and could be fixed sooner.
4. **Persist the legal consent fields to `Customers`** (Gap 1) — small,
   independent fix, not blocking on the rest of this sequence.
5. **Build the `doPost` Web App + decouple registration logic** per
   `ADD_G1-06D` — the data bridge this specification's fields will flow
   through.
6. **Add language/currency branching to `generateInitialTasks` and the
   email functions** (Gap 4) — needed before a non-JP customer can be
   correctly onboarded end to end.
7. **Build/confirm the Vidcel Onboarding Page UI** against this field set.
8. **Wire the page to the new endpoint**, testing with the existing Google
   Form still live in parallel (per `ADD_G1-06D`'s backward-compatibility
   note).
9. **Replace the Stripe self-attestation with real verification** (Gap 2 /
   G1-06) — highest-value trust fix, independent timing from the rest.
10. **Independent E2E validation, per market (JP and US separately)** — no
    evidence inherited from the old Google Form, per `ADD_G1-06D`'s
    explicit instruction. This is what would move PM OS `04_Gates` items
    back to Completed with real, new evidence.

Each numbered step above is a candidate future Task ID, not an
authorization to proceed — per this task's instruction, nothing here has
been implemented.
