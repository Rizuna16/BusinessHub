"""
Tests for TaxCalculationService (Feature #37)
"""
import pytest
from decimal import Decimal
from app.modules.accounting.schemas import TaxTreatment, PricingMode
from app.modules.accounting.tax_calculation import tax_calculation_service, TaxCalculationService


class TestTaxCalculationEngine:
    def test_standard_non_luxury_exclusive(self):
        """
        Commercial amount = 100,000
        DPP = 100,000 × 11/12 = 91,666.67
        PPN = 91,666.67 × 12% = 11,000.00
        Gross = 111,000.00
        Effective PPN = 11%
        """
        res = tax_calculation_service.calculate_line_tax(
            quantity=Decimal("1"),
            unit_price=Decimal("100000"),
            discount_amount=Decimal("0"),
            tax_treatment=TaxTreatment.STANDARD_NON_LUXURY,
            pricing_mode=PricingMode.TAX_EXCLUSIVE,
        )
        assert res.commercial_amount == Decimal("100000.00")
        assert res.dpp == Decimal("91666.67")
        assert res.tax_amount == Decimal("11000.00")
        assert res.gross_total == Decimal("111000.00")
        assert res.statutory_rate == Decimal("0.12")

    def test_standard_non_luxury_inclusive(self):
        """
        Gross amount = 111,000
        PPN = 111,000 × 11/111 = 11,000.00
        Commercial net = 100,000.00
        DPP = 100,000 × 11/12 = 91,666.67
        """
        res = tax_calculation_service.calculate_line_tax(
            quantity=Decimal("1"),
            unit_price=Decimal("111000"),
            discount_amount=Decimal("0"),
            tax_treatment=TaxTreatment.STANDARD_NON_LUXURY,
            pricing_mode=PricingMode.TAX_INCLUSIVE,
        )
        assert res.gross_total == Decimal("111000.00")
        assert res.tax_amount == Decimal("11000.00")
        assert res.commercial_amount == Decimal("100000.00")
        assert res.dpp == Decimal("91666.67")

    def test_discount_applied_before_tax(self):
        """
        Subtotal = 200,000
        Discount = 50,000
        Commercial Net = 150,000
        DPP = 150,000 × 11/12 = 137,500.00
        PPN = 137,500 × 12% = 16,500.00
        Gross = 166,500.00
        """
        res = tax_calculation_service.calculate_line_tax(
            quantity=Decimal("2"),
            unit_price=Decimal("100000"),
            discount_amount=Decimal("50000"),
            tax_treatment=TaxTreatment.STANDARD_NON_LUXURY,
            pricing_mode=PricingMode.TAX_EXCLUSIVE,
        )
        assert res.commercial_amount == Decimal("150000.00")
        assert res.dpp == Decimal("137500.00")
        assert res.tax_amount == Decimal("16500.00")
        assert res.gross_total == Decimal("166500.00")

    def test_non_taxable_treatment(self):
        res = tax_calculation_service.calculate_line_tax(
            quantity=Decimal("5"),
            unit_price=Decimal("20000"),
            discount_amount=Decimal("10000"),
            tax_treatment=TaxTreatment.NON_TAXABLE,
            pricing_mode=PricingMode.TAX_EXCLUSIVE,
        )
        assert res.commercial_amount == Decimal("90000.00")
        assert res.dpp == Decimal("0.00")
        assert res.tax_amount == Decimal("0.00")
        assert res.gross_total == Decimal("90000.00")

    def test_quantity_price_validations(self):
        with pytest.raises(ValueError, match="Quantity must be greater than 0"):
            tax_calculation_service.calculate_line_tax(
                quantity=Decimal("0"), unit_price=Decimal("100"), discount_amount=Decimal("0"),
                tax_treatment=TaxTreatment.STANDARD_NON_LUXURY, pricing_mode=PricingMode.TAX_EXCLUSIVE
            )

        with pytest.raises(ValueError, match="Unit price cannot be negative"):
            tax_calculation_service.calculate_line_tax(
                quantity=Decimal("1"), unit_price=Decimal("-100"), discount_amount=Decimal("0"),
                tax_treatment=TaxTreatment.STANDARD_NON_LUXURY, pricing_mode=PricingMode.TAX_EXCLUSIVE
            )
