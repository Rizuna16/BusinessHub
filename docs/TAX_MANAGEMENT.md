# Feature #37 — Tax Management (PPN/VAT) MVP

## Overview

Feature #37 implements PPN/VAT (Pajak Pertambahan Nilai / Value Added Tax) management for BusinessHub. It provides business-level tax configuration, centralized tax calculation, VAT accounting integration, and a monthly tax summary report.

**IMPORTANT DISCLAIMER:** This is an application-level tax configuration MVP. It is NOT a complete Indonesian tax compliance system. It does NOT implement SPT filing, e-Faktur generation, Coretax integration, PPh, luxury goods tax (PPnBM), import/export VAT, or tax authority integrations.

## Tax Treatments

### STANDARD_NON_LUXURY
Standard PPN treatment for domestic non-luxury goods and services.

**Statutory Rate:** 12% (Indonesian VAT per UU HPP No. 7/2021 as amended)  
**DPP Factor:** 11/12 of commercial net amount  
**Effective VAT Burden:** 11% of commercial amount

### NON_TAXABLE
Product/service is not subject to PPN. PPN = 0 regardless of configuration.

## Pricing Modes

### TAX_EXCLUSIVE
Unit price is exclusive of VAT. VAT is calculated and added separately.

```
commercial_amount = (quantity × unit_price) - discount
DPP = commercial_amount × 11/12
PPN = DPP × 12%
gross_total = commercial_amount + PPN
```

### TAX_INCLUSIVE
Unit price includes VAT. VAT is extracted from the gross amount.

```
gross_amount = (quantity × unit_price) - discount
PPN = gross_amount × 11/111
commercial_amount = gross_amount - PPN
DPP = commercial_amount × 11/12
```

## Rounding Policy

- All calculations use Python `Decimal` exclusively
- No floating-point arithmetic
- Monetary values rounded to 2 decimal places using `ROUND_HALF_UP`
- DPP is rounded separately before PPN calculation
- PPN is rounded before final total calculation

## TaxConfiguration

Each business has exactly one `TaxConfiguration`:
- `tax_enabled: bool` (default: False) — Application flag, NOT a legal PKP assertion
- `pricing_mode: PricingMode` (default: TAX_EXCLUSIVE)
- `default_tax_treatment: TaxTreatment` (default: STANDARD_NON_LUXURY)

**Authorization:**
- Owner/Admin: read and update
- Member: read only
- Business-scoped isolation enforced

## Product Tax Treatment

Each product has a `tax_treatment` field:
- `STANDARD_NON_LUXURY` (default)
- `NON_TAXABLE`

Product tax treatment is resolved at transaction calculation time and snapshotted.

## TaxSnapshot

Historical finalized transactions preserve their original tax calculation via `TaxSnapshot`:
- tax_treatment
- pricing_mode
- statutory_rate
- dpp_factor
- commercial_amount
- dpp
- tax_amount

Historical transactions are NEVER recalculated when configuration changes.

## Accounting Integration

### Tax-Enabled Taxable Sale
```
Dr 1200 Accounts Receivable = gross_total
Cr 4100 Sales Revenue = commercial_amount (net)
Cr 2200 Output VAT = PPN
```

### Tax-Enabled Taxable Purchase (Creditable)
```
Dr 1300 Inventory Assets = commercial_amount (net)
Dr 1400 Input VAT = PPN
Cr 2100 Accounts Payable = gross_total
```

### System Accounts Added
- `1400`: PPN Masukan (Input VAT) — ASSET, DEBIT normal
- `2200`: PPN Keluaran (Output VAT) — LIABILITY, CREDIT normal

## Returns

Sales/Purchase returns use the **original historical tax snapshot**. They do NOT recalculate using current tax configuration or product settings.

## Manual tax_amount Transition

- Existing finalized historical transactions preserve their recorded tax amounts
- New transactions must use TaxCalculationService for automatic calculation
- Existing draft transactions recalculate on update/finalization

## Tax Summary

Monthly tax summary via: `GET /accounting/reports/tax-summary?year=YYYY&month=MM`

Returns:
- Output VAT (credits on 2200)
- Input VAT (debits on 1400)
- Net VAT (Output - Input)
- Taxable sales/purchases count

Excludes DRAFT and VOIDED journals.

## Limitations

This MVP does NOT include:
- PPh (Income Tax)
- Luxury goods (PPnBM)
- Special DPP mechanisms
- Import/Export VAT
- e-Faktur generation
- SPT filing
- Tax payment settlement
- Supplier PKP verification
- Tax authority integration
- Multi-currency tax
- Multi-country VAT
- Tax year-end workflow
- Automatic tax period generation
