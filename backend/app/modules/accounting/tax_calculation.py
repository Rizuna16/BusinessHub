"""
TaxCalculationService — Feature #37
Centralized PPN/VAT calculation engine for BusinessHub.
All tax calculations MUST use this service.
"""

from decimal import Decimal, ROUND_HALF_UP
from app.modules.accounting.schemas import TaxTreatment, PricingMode, TaxCalculationResult


# Statutory rates and DPP factors for STANDARD_NON_LUXURY
STANDARD_NON_LUXURY_STATUTORY_RATE = Decimal("0.12")
STANDARD_NON_LUXURY_DPP_FACTOR = Decimal("11") / Decimal("12")


class TaxCalculationService:
    """
    Pure, stateless, deterministic tax calculation engine.
    Uses Decimal-only arithmetic. 2 decimal places monetary precision.
    """

    def calculate_line_tax(
        self,
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_treatment: TaxTreatment,
        pricing_mode: PricingMode,
    ) -> TaxCalculationResult:
        """
        Calculate tax for a single transaction line.
        
        This is the centralized tax engine. All sales/purchase/returns
        MUST use this method.
        """
        if quantity <= Decimal("0"):
            raise ValueError("Quantity must be greater than 0")
        if unit_price < Decimal("0"):
            raise ValueError("Unit price cannot be negative")
        if discount_amount < Decimal("0"):
            raise ValueError("Discount amount cannot be negative")

        if tax_treatment == TaxTreatment.NON_TAXABLE:
            return self._calculate_non_taxable(
                quantity, unit_price, discount_amount, pricing_mode
            )

        return self._calculate_standard_non_luxury(
            quantity, unit_price, discount_amount, pricing_mode
        )

    def _calculate_standard_non_luxury(
        self,
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        pricing_mode: PricingMode,
    ) -> TaxCalculationResult:
        """Calculate PPN for STANDARD_NON_LUXURY treatment."""
        statutory_rate = STANDARD_NON_LUXURY_STATUTORY_RATE
        dpp_factor = STANDARD_NON_LUXURY_DPP_FACTOR

        if pricing_mode == PricingMode.TAX_EXCLUSIVE:
            return self._calc_exclusive(
                quantity, unit_price, discount_amount,
                statutory_rate, dpp_factor
            )
        else:
            return self._calc_inclusive(
                quantity, unit_price, discount_amount,
                statutory_rate, dpp_factor
            )

    def _calc_exclusive(
        self,
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        statutory_rate: Decimal,
        dpp_factor: Decimal,
    ) -> TaxCalculationResult:
        """
        TAX-EXCLUSIVE formula:
        commercial_amount = (quantity × unit_price) - discount
        DPP = commercial_amount × 11/12 (rounded to 2 decimals)
        PPN = DPP × 12% (rounded to 2 decimals)
        gross_total = commercial_amount + PPN
        """
        commercial_amount = (quantity * unit_price) - discount_amount

        # DPP Calculation: commercial_amount × 11/12
        raw_dpp = commercial_amount * dpp_factor
        dpp = raw_dpp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # PPN Calculation: DPP × 12%
        raw_ppn = dpp * statutory_rate
        ppn = raw_ppn.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        gross_total = (commercial_amount + ppn).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return TaxCalculationResult(
            tax_treatment=TaxTreatment.STANDARD_NON_LUXURY,
            pricing_mode=PricingMode.TAX_EXCLUSIVE,
            statutory_rate=statutory_rate,
            dpp_factor=dpp_factor,
            commercial_amount=commercial_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            dpp=dpp,
            tax_amount=ppn,
            gross_total=gross_total,
        )

    def _calc_inclusive(
        self,
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        statutory_rate: Decimal,
        dpp_factor: Decimal,
    ) -> TaxCalculationResult:
        """
        TAX-INCLUSIVE formula for STANDARD_NON_LUXURY:
        gross_amount = (quantity × unit_price) - discount
        PPN = gross_amount × 11/111 (rounded to 2 decimals)
        commercial_amount = gross_amount - PPN
        DPP = commercial_amount × 11/12 (rounded to 2 decimals)
        """
        gross_amount = (quantity * unit_price) - discount_amount

        # PPN Calculation: gross_amount × 11/111
        inclusive_factor = Decimal("11") / Decimal("111")
        raw_ppn = gross_amount * inclusive_factor
        ppn = raw_ppn.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Commercial amount = gross - PPN
        commercial_amount = (gross_amount - ppn).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # DPP: commercial_amount × 11/12
        raw_dpp = commercial_amount * dpp_factor
        dpp = raw_dpp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return TaxCalculationResult(
            tax_treatment=TaxTreatment.STANDARD_NON_LUXURY,
            pricing_mode=PricingMode.TAX_INCLUSIVE,
            statutory_rate=statutory_rate,
            dpp_factor=dpp_factor,
            commercial_amount=commercial_amount,
            dpp=dpp,
            tax_amount=ppn,
            gross_total=gross_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )

    def _calculate_non_taxable(
        self,
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        pricing_mode: PricingMode,
    ) -> TaxCalculationResult:
        """NON_TAXABLE: PPN = 0."""
        commercial_amount = (quantity * unit_price) - discount_amount
        gross_total = commercial_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return TaxCalculationResult(
            tax_treatment=TaxTreatment.NON_TAXABLE,
            pricing_mode=pricing_mode,
            statutory_rate=Decimal("0"),
            dpp_factor=Decimal("0"),
            commercial_amount=commercial_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            dpp=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            gross_total=gross_total,
        )


tax_calculation_service = TaxCalculationService()
