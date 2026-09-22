"""
Feature #64 — Discount & Promotional Pricing Rules Tests

Tests discount rule CRUD, validation, evaluation, integration,
manual override, tenant isolation, and regression.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from app.modules.pricing.service import PricingService
from app.modules.pricing.schemas import DiscountRuleCreate, DiscountRuleUpdate
from app.modules.pricing.repository import InMemoryDiscountRuleRepository


@pytest.fixture(autouse=True)
def clear_discount_repos():
    InMemoryDiscountRuleRepository.clear()
    yield
    InMemoryDiscountRuleRepository.clear()


@pytest.fixture
def pricing_svc():
    return PricingService()


BIZ = "biz-001"
USER = "user-001"
PROD = "prod-001"
VARIANT = "var-001"


def _mock_admin():
    mock = MagicMock()
    mock.role = "OWNER"
    return mock


def _mock_member():
    mock = MagicMock()
    mock.role = "MEMBER"
    return mock


class TestDiscountRuleCRUD:
    @pytest.mark.asyncio
    async def test_create_percentage_rule(self, pricing_svc):
        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            with patch.object(pricing_svc.product_repo, "get_by_id", new_callable=AsyncMock, return_value=MagicMock()):
                data = DiscountRuleCreate(
                    name="Summer 10%",
                    type="PERCENTAGE",
                    value=Decimal("10.00"),
                    product_id=PROD,
                    starts_at=datetime.now(timezone.utc),
                )
                result = await pricing_svc.discount_rule_create(BIZ, USER, data)
                assert result.name == "Summer 10%"
                assert result.type == "PERCENTAGE"
                assert result.status == "ACTIVE"
                assert result.product_id == PROD

    @pytest.mark.asyncio
    async def test_create_fixed_rule(self, pricing_svc):
        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            with patch.object(pricing_svc.variant_repo, "get_by_id", new_callable=AsyncMock, return_value=MagicMock()):
                data = DiscountRuleCreate(
                    name="Fixed $5",
                    type="FIXED",
                    value=Decimal("5.0000"),
                    variant_id=VARIANT,
                    starts_at=datetime.now(timezone.utc),
                )
                result = await pricing_svc.discount_rule_create(BIZ, USER, data)
                assert result.type == "FIXED"
                assert result.variant_id == VARIANT

    @pytest.mark.asyncio
    async def test_get_rule(self, pricing_svc):
        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            with patch.object(pricing_svc.product_repo, "get_by_id", new_callable=AsyncMock, return_value=MagicMock()):
                data = DiscountRuleCreate(
                    name="R1", type="PERCENTAGE", value=Decimal("5.00"),
                    product_id=PROD, starts_at=datetime.now(timezone.utc),
                )
                created = await pricing_svc.discount_rule_create(BIZ, USER, data)

        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_member()):
            fetched = await pricing_svc.discount_rule_get(BIZ, USER, created.id)
            assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_list_rules(self, pricing_svc):
        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            with patch.object(pricing_svc.product_repo, "get_by_id", new_callable=AsyncMock, return_value=MagicMock()):
                for i in range(3):
                    data = DiscountRuleCreate(
                        name=f"R{i}", type="PERCENTAGE", value=Decimal("1.00"),
                        product_id=PROD, starts_at=datetime.now(timezone.utc),
                    )
                    await pricing_svc.discount_rule_create(BIZ, USER, data)

        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_member()):
            result = await pricing_svc.discount_rule_list(BIZ, USER)
            assert result.total == 3

    @pytest.mark.asyncio
    async def test_update_rule(self, pricing_svc):
        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            with patch.object(pricing_svc.product_repo, "get_by_id", new_callable=AsyncMock, return_value=MagicMock()):
                data = DiscountRuleCreate(
                    name="Old", type="PERCENTAGE", value=Decimal("5.00"),
                    product_id=PROD, starts_at=datetime.now(timezone.utc),
                )
                created = await pricing_svc.discount_rule_create(BIZ, USER, data)

        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            update_data = DiscountRuleUpdate(name="New", value=Decimal("25.00"))
            updated = await pricing_svc.discount_rule_update(BIZ, USER, created.id, update_data)
            assert updated.name == "New"

    @pytest.mark.asyncio
    async def test_archive_rule(self, pricing_svc):
        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            with patch.object(pricing_svc.product_repo, "get_by_id", new_callable=AsyncMock, return_value=MagicMock()):
                data = DiscountRuleCreate(
                    name="To Archive", type="FIXED", value=Decimal("1.00"),
                    product_id=PROD, starts_at=datetime.now(timezone.utc),
                )
                created = await pricing_svc.discount_rule_create(BIZ, USER, data)

        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            archived = await pricing_svc.discount_rule_archive(BIZ, USER, created.id)
            assert archived.status == "ARCHIVED"

    @pytest.mark.asyncio
    async def test_activate_and_deactivate(self, pricing_svc):
        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            with patch.object(pricing_svc.product_repo, "get_by_id", new_callable=AsyncMock, return_value=MagicMock()):
                data = DiscountRuleCreate(
                    name="Toggle", type="FIXED", value=Decimal("2.00"),
                    product_id=PROD, starts_at=datetime.now(timezone.utc),
                )
                created = await pricing_svc.discount_rule_create(BIZ, USER, data)

        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            deactivated = await pricing_svc.discount_rule_deactivate(BIZ, USER, created.id)
            assert deactivated.status == "INACTIVE"

            activated = await pricing_svc.discount_rule_activate(BIZ, USER, created.id)
            assert activated.status == "ACTIVE"


class TestDiscountRuleValidation:
    @pytest.mark.asyncio
    async def test_percentage_over_100_rejected(self, pricing_svc):
        with patch.object(pricing_svc.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=_mock_admin()):
            with patch.object(pricing_svc.product_repo, "get_by_id", new_callable=AsyncMock, return_value=MagicMock()):
                with pytest.raises(Exception):
                    DiscountRuleCreate(
                        name="Bad", type="PERCENTAGE", value=Decimal("105.00"),
                        product_id=PROD, starts_at=datetime.now(timezone.utc),
                    )

    @pytest.mark.asyncio
    async def test_negative_fixed_rejected(self, pricing_svc):
        with pytest.raises(Exception):
            DiscountRuleCreate(
                name="Bad", type="FIXED", value=Decimal("-5.00"),
                product_id=PROD, starts_at=datetime.now(timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_neither_product_nor_variant_rejected(self, pricing_svc):
        with pytest.raises(Exception):
            DiscountRuleCreate(
                name="Bad", type="FIXED", value=Decimal("5.00"),
                starts_at=datetime.now(timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_both_product_and_variant_rejected(self, pricing_svc):
        with pytest.raises(Exception):
            DiscountRuleCreate(
                name="Bad", type="FIXED", value=Decimal("5.00"),
                product_id=PROD, variant_id=VARIANT,
                starts_at=datetime.now(timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_ends_before_starts_rejected(self, pricing_svc):
        now = datetime.now(timezone.utc)
        with pytest.raises(Exception):
            DiscountRuleCreate(
                name="Bad", type="FIXED", value=Decimal("5.00"),
                product_id=PROD,
                starts_at=now, ends_at=now - timedelta(hours=1),
            )


class TestDiscountEvaluation:
    @pytest.mark.asyncio
    async def test_percentage_discount(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "10% off", "type": "PERCENTAGE", "value": Decimal("10.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, rule_id, rule_name = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("2"), Decimal("1000.00"), "IDR", now,
        )
        assert discount == Decimal("200.00")
        assert rule_id is not None
        assert rule_name == "10% off"

    @pytest.mark.asyncio
    async def test_fixed_discount(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "$5 off", "type": "FIXED", "value": Decimal("5.0000"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, rule_id, rule_name = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("2"), Decimal("1000.00"), "IDR", now,
        )
        assert discount == Decimal("5.0000")

    @pytest.mark.asyncio
    async def test_no_matching_product(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "Other", "type": "PERCENTAGE", "value": Decimal("10.00"),
            "product_id": "other-prod", "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, rule_id, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("0")
        assert rule_id is None

    @pytest.mark.asyncio
    async def test_inactive_rule_not_applied(self, pricing_svc):
        now = datetime.now(timezone.utc)
        rule = await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "Inactive", "type": "PERCENTAGE", "value": Decimal("10.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        await pricing_svc.discount_rule_repo.update_status(rule.id, BIZ, "INACTIVE")
        discount, rule_id, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("0")

    @pytest.mark.asyncio
    async def test_before_start_not_applied(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "Future", "type": "PERCENTAGE", "value": Decimal("10.00"),
            "product_id": PROD, "starts_at": now + timedelta(days=1),
            "priority": 100,
        })
        discount, rule_id, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("0")

    @pytest.mark.asyncio
    async def test_after_expiry_not_applied(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "Expired", "type": "PERCENTAGE", "value": Decimal("10.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=10),
            "ends_at": now - timedelta(days=1), "priority": 100,
        })
        discount, rule_id, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("0")

    @pytest.mark.asyncio
    async def test_priority_wins_over_higher_priority(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "Low Priority", "type": "FIXED", "value": Decimal("1.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 200,
        })
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "High Priority", "type": "FIXED", "value": Decimal("9.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 1,
        })
        discount, rule_id, rule_name = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("9.00")
        assert rule_name == "High Priority"

    @pytest.mark.asyncio
    async def test_discount_capped_at_subtotal(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "Big Fixed", "type": "FIXED", "value": Decimal("999.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, _, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_zero_quantity_returns_zero(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "X", "type": "PERCENTAGE", "value": Decimal("10.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "priority": 100,
        })
        discount, rule_id, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("0"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("0")
        assert rule_id is None

    @pytest.mark.asyncio
    async def test_percentage_100_gives_full_subtotal(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "100% Off", "type": "PERCENTAGE", "value": Decimal("100.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, _, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("3"), Decimal("500.00"), "IDR", now,
        )
        assert discount == Decimal("1500.00")


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_rules_from_other_business_not_applied(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create("other-biz", {
            "name": "Other Biz", "type": "PERCENTAGE", "value": Decimal("50.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, rule_id, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("0")
        assert rule_id is None


class TestQuotationSalesIntegration:
    @pytest.mark.asyncio
    async def test_quotation_create_evaluates_discount(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "10% off", "type": "PERCENTAGE", "value": Decimal("10.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        from app.modules.sales_order.repository import InMemoryQuotationRepository
        from app.modules.sales_order.quotation_service import QuotationService
        from unittest.mock import AsyncMock, patch
        from app.modules.sales_order.schemas import QuotationLineCreate

        InMemoryQuotationRepository.clear()
        quotation_repo = InMemoryQuotationRepository()
        mock_repo = AsyncMock()
        mock_repo.get_quotation_by_id = AsyncMock(return_value=MagicMock(
            id="q1", business_id=BIZ, status="DRAFT"
        ))
        mock_repo.get_line_by_id = AsyncMock(return_value=None)
        mock_repo.create_line = AsyncMock(return_value=MagicMock(
            id="l1", quotation_id="q1", product_id=PROD, variant_id=None,
            description="Test", quantity=Decimal("2"), unit_price=Decimal("1000"),
            discount_amount=Decimal("200.00"), discount_rule_id="r1",
            discount_rule_name_snapshot="10% off", tax_amount=Decimal("0"),
            line_subtotal=Decimal("2000"), line_total=Decimal("1800"),
            created_at=now, updated_at=now,
            model_dump=lambda: {
                "id": "l1", "quotation_id": "q1", "product_id": PROD, "variant_id": None,
                "description": "Test", "quantity": Decimal("2"), "unit_price": Decimal("1000"),
                "discount_amount": Decimal("200.00"), "discount_rule_id": "r1",
                "discount_rule_name_snapshot": "10% off", "tax_amount": Decimal("0"),
                "line_subtotal": Decimal("2000"), "line_total": Decimal("1800"),
                "created_at": now, "updated_at": now,
            }
        ))
        mock_repo.update_quotation = AsyncMock()

        svc = QuotationService(quotation_repo=mock_repo)

        payload = QuotationLineCreate(
            product_id=PROD, variant_id=None, description="Test",
            quantity=Decimal("2"), unit_price=Decimal("1000"),
            discount_amount=Decimal("0"), tax_amount=Decimal("0"),
        )

        with patch.object(svc, '_validate_access', new_callable=AsyncMock):
            with patch.object(svc, '_validate_product_and_variant', new_callable=AsyncMock, return_value=(PROD, None)):
                with patch.object(svc, '_recalculate_totals', new_callable=AsyncMock):
                    result = await svc.add_line(BIZ, "q1", "u1", payload)
                    mock_repo.create_line.assert_called_once()
                    call_kwargs = mock_repo.create_line.call_args[1]
                    assert call_kwargs["discount_amount"] == Decimal("200.00")
                    assert call_kwargs["discount_rule_id"] is not None

    @pytest.mark.asyncio
    async def test_quotation_update_re_evaluates(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "15% off", "type": "PERCENTAGE", "value": Decimal("15.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        from unittest.mock import AsyncMock, patch, MagicMock
        from app.modules.sales_order.quotation_service import QuotationService
        from app.modules.sales_order.schemas import QuotationLineUpdate

        mock_repo = AsyncMock()
        mock_repo.get_quotation_by_id = AsyncMock(return_value=MagicMock(
            id="q1", business_id=BIZ, status="DRAFT"
        ))
        existing_line = MagicMock()
        existing_line.product_id = PROD
        existing_line.variant_id = None
        existing_line.quantity = Decimal("1")
        existing_line.unit_price = Decimal("1000")
        existing_line.discount_amount = Decimal("0")
        existing_line.tax_amount = Decimal("0")
        mock_repo.get_line_by_id = AsyncMock(return_value=existing_line)
        mock_repo.update_line = AsyncMock(return_value=MagicMock(
            id="l1", quotation_id="q1", product_id=PROD, variant_id=None,
            description="Test", quantity=Decimal("2"), unit_price=Decimal("1000"),
            discount_amount=Decimal("300.00"), discount_rule_id="r1",
            discount_rule_name_snapshot="15% off", tax_amount=Decimal("0"),
            line_subtotal=Decimal("2000"), line_total=Decimal("1700"),
            created_at=now, updated_at=now,
            model_dump=lambda: {
                "id": "l1", "quotation_id": "q1", "product_id": PROD, "variant_id": None,
                "description": "Test", "quantity": Decimal("2"), "unit_price": Decimal("1000"),
                "discount_amount": Decimal("300.00"), "discount_rule_id": "r1",
                "discount_rule_name_snapshot": "15% off", "tax_amount": Decimal("0"),
                "line_subtotal": Decimal("2000"), "line_total": Decimal("1700"),
                "created_at": now, "updated_at": now,
            }
        ))
        mock_repo.update_quotation = AsyncMock()

        svc = QuotationService(quotation_repo=mock_repo)

        payload = QuotationLineUpdate(
            quantity=Decimal("2"), unit_price=Decimal("1000"),
        )

        with patch.object(svc, '_validate_access', new_callable=AsyncMock):
            with patch.object(svc, '_validate_product_and_variant', new_callable=AsyncMock, return_value=(PROD, None)):
                with patch.object(svc, '_recalculate_totals', new_callable=AsyncMock):
                    await svc.update_line(BIZ, "q1", "l1", "u1", payload)
                    mock_repo.update_line.assert_called_once()
                    call_kwargs = mock_repo.update_line.call_args[1]
                    assert call_kwargs["discount_amount"] == Decimal("300.00")
                    assert call_kwargs["discount_rule_id"] is not None

    @pytest.mark.asyncio
    async def test_sales_update_re_evaluates(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "20% off", "type": "PERCENTAGE", "value": Decimal("20.00"),
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        from unittest.mock import AsyncMock, patch, MagicMock
        from app.modules.sales.service import SalesService
        from app.modules.sales.schemas import SalesLineUpdate

        mock_repo = AsyncMock()
        mock_repo.get_sales_by_id = AsyncMock(return_value=MagicMock(
            id="s1", business_id=BIZ, status="DRAFT", sales_date=now
        ))
        existing_line = MagicMock()
        existing_line.product_id = PROD
        existing_line.variant_id = None
        existing_line.quantity = Decimal("1")
        existing_line.unit_price = Decimal("500")
        existing_line.discount_amount = Decimal("0")
        existing_line.tax_amount = Decimal("0")
        existing_line.id = "l1"
        mock_repo.get_line_by_id = AsyncMock(return_value=existing_line)
        updated_line_mock = MagicMock(
            id="l1", sales_id="s1", product_id=PROD, variant_id=None,
            description="Test", quantity=Decimal("2"), unit_price=Decimal("500"),
            discount_amount=Decimal("200.00"), discount_rule_id="r1",
            discount_rule_name_snapshot="20% off", tax_amount=Decimal("0"),
            line_subtotal=Decimal("1000"), line_total=Decimal("800"),
            created_at=now, updated_at=now,
            model_dump=lambda: {
                "id": "l1", "sales_id": "s1", "product_id": PROD, "variant_id": None,
                "description": "Test", "quantity": Decimal("2"), "unit_price": Decimal("500"),
                "discount_amount": Decimal("200.00"), "discount_rule_id": "r1",
                "discount_rule_name_snapshot": "20% off", "tax_amount": Decimal("0"),
                "line_subtotal": Decimal("1000"), "line_total": Decimal("800"),
                "created_at": now, "updated_at": now,
            }
        )
        mock_repo.update_line = AsyncMock(return_value=updated_line_mock)
        mock_repo.update_sales = AsyncMock()
        mock_repo.list_lines_for_sales = AsyncMock(return_value=[])

        svc = SalesService(sales_repo=mock_repo)

        payload = SalesLineUpdate(
            quantity=Decimal("2"), unit_price=Decimal("500"),
        )

        with patch.object(svc, '_validate_access', new_callable=AsyncMock):
            with patch.object(svc, '_validate_product_and_variant', new_callable=AsyncMock, return_value=(PROD, None)):
                with patch.object(svc, '_recalculate_totals', new_callable=AsyncMock):
                    with patch.object(svc, '_find_active_price_entry', new_callable=AsyncMock, return_value=None):
                        await svc.update_line(BIZ, "s1", "l1", "u1", payload)
                        mock_repo.update_line.assert_called_once()
                        call_kwargs = mock_repo.update_line.call_args[1]
                        assert call_kwargs["discount_amount"] == Decimal("200.00")
                        assert call_kwargs["discount_rule_id"] is not None

    @pytest.mark.asyncio
    async def test_quotation_to_order_preserves_snapshot(self, pricing_svc):
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.modules.sales_order.quotation_service import QuotationService

        mock_q_repo = AsyncMock()
        mock_so_repo = AsyncMock()
        q_lines = [MagicMock(
            product_id=PROD, variant_id=None, description="Item",
            quantity=Decimal("1"), unit_price=Decimal("1000"),
            discount_amount=Decimal("100"), tax_amount=Decimal("0"),
            discount_rule_id="rule-123", discount_rule_name_snapshot="10% Off",
        )]
        mock_q_repo.list_lines_for_quotation = AsyncMock(return_value=q_lines)
        mock_q_repo.get_quotation_by_id = AsyncMock(return_value=MagicMock(
            id="q1", business_id=BIZ, status="ACCEPTED",
            customer_id="c1", branch_id="b1", warehouse_id="w1",
        ))
        mock_q_repo.update_quotation = AsyncMock()
        mock_so_repo.get_next_order_sequence = AsyncMock(return_value=1)
        mock_so_repo.create_order = AsyncMock(return_value=MagicMock(id="so1"))
        mock_so_repo.create_line = AsyncMock(return_value=MagicMock(
            id="sol1", model_dump=lambda: {}
        ))

        svc = QuotationService(quotation_repo=mock_q_repo, sales_order_repo=mock_so_repo)
        payload = MagicMock()
        payload.notes = None

        with patch.object(svc, '_validate_access', new_callable=AsyncMock):
            result = await svc._convert_quotation_impl(BIZ, "q1", "u1", payload)
            mock_so_repo.create_line.assert_called_once()
            call_kwargs = mock_so_repo.create_line.call_args[1]
            assert call_kwargs["discount_rule_id"] == "rule-123"
            assert call_kwargs["discount_rule_name_snapshot"] == "10% Off"

    @pytest.mark.asyncio
    async def test_fixed_currency_match(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "Fixed IDR 50k", "type": "FIXED", "value": Decimal("50000"),
            "currency": "IDR",
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, rule_id, rule_name = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("200000"), "IDR", now,
        )
        assert discount == Decimal("50000")
        assert rule_id is not None
        assert rule_name == "Fixed IDR 50k"

    @pytest.mark.asyncio
    async def test_fixed_currency_mismatch_rejected(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "Fixed USD 5", "type": "FIXED", "value": Decimal("5.00"),
            "currency": "USD",
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, rule_id, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("1"), Decimal("100.00"), "IDR", now,
        )
        assert discount == Decimal("0")
        assert rule_id is None

    @pytest.mark.asyncio
    async def test_percentage_currency_independent(self, pricing_svc):
        now = datetime.now(timezone.utc)
        await pricing_svc.discount_rule_repo.create(BIZ, {
            "name": "10% global", "type": "PERCENTAGE", "value": Decimal("10.00"),
            "currency": "USD",
            "product_id": PROD, "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1), "priority": 100,
        })
        discount, rule_id, _ = await pricing_svc.evaluate_discount(
            BIZ, PROD, None, Decimal("2"), Decimal("1000"), "IDR", now,
        )
        assert discount == Decimal("200.00")
        assert rule_id is not None
