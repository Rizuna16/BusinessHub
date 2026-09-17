from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException, status

from app.modules.authentication.schemas import PlatformRole, UserInDB
from app.modules.authentication.repository import AbstractUserRepository, user_repository
from app.modules.business.schemas import BusinessStatus, BusinessInDB, BusinessUpdate
from app.modules.business.repository import AbstractBusinessRepository, business_repository
from app.modules.business_membership.repository import AbstractBusinessMembershipRepository, business_membership_repository
from app.modules.branch.repository import AbstractBranchRepository, branch_repository
from app.modules.subscription.service import SubscriptionService, subscription_service
from app.modules.subscription.schemas import SubscriptionStatus, SubscriptionResponse, SubscriptionOverrideInput
from app.modules.platform_admin.schemas import (
    PlatformAuditLogCreate, PlatformAuditLogResponse, PlatformDashboardResponse,
    PlatformUserResponse, PlatformBusinessDetailResponse, BusinessActionInput
)
from app.modules.platform_admin.repository import AbstractPlatformAuditRepository, platform_audit_repository


class PlatformAdminService:
    def __init__(
        self,
        user_repo: AbstractUserRepository = user_repository,
        business_repo: AbstractBusinessRepository = business_repository,
        membership_repo: AbstractBusinessMembershipRepository = business_membership_repository,
        branch_repo: AbstractBranchRepository = branch_repository,
        sub_service: SubscriptionService = subscription_service,
        audit_repo: AbstractPlatformAuditRepository = platform_audit_repository,
    ):
        self.user_repo = user_repo
        self.business_repo = business_repo
        self.membership_repo = membership_repo
        self.branch_repo = branch_repo
        self.sub_service = sub_service
        self.audit_repo = audit_repo

    async def require_superadmin(self, user_id: str) -> UserInDB:
        """
        Verify that user exists, is_active, and possesses SUPER_ADMIN platform authority.
        Always validates directly against current Account repository state.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform account is inactive or access denied."
            )
        if user.platform_role != PlatformRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform Super Admin authority required."
            )
        return user

    async def log_audit(
        self,
        actor: UserInDB,
        action: str,
        target_type: str,
        target_id: str,
        target_business_id: Optional[str] = None,
        reason: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        result: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlatformAuditLogResponse:
        entry = PlatformAuditLogCreate(
            actor_account_id=actor.id,
            actor_email=actor.email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_business_id=target_business_id,
            reason=reason,
            before_state=before_state,
            after_state=after_state,
            result=result,
            metadata=metadata,
        )
        created = await self.audit_repo.create(entry)
        return PlatformAuditLogResponse.model_validate(created)

    async def get_dashboard(self, superadmin: UserInDB) -> PlatformDashboardResponse:
        all_businesses = list(self.business_repo._businesses.values()) if hasattr(self.business_repo, "_businesses") else []
        total_businesses = len(all_businesses)
        active_businesses = sum(1 for b in all_businesses if b.status == BusinessStatus.ACTIVE)
        suspended_businesses = sum(1 for b in all_businesses if b.status == BusinessStatus.SUSPENDED)
        archived_businesses = sum(1 for b in all_businesses if b.status == BusinessStatus.ARCHIVED)

        all_users = await self.user_repo.list_all()
        total_accounts = len(all_users)

        all_subs = await self.sub_service.list_all()
        active_subscriptions = sum(1 for s in all_subs if s.status == SubscriptionStatus.ACTIVE)
        expired_subscriptions = sum(1 for s in all_subs if s.status == SubscriptionStatus.EXPIRED)

        mrr_idr = Decimal("50000.00") * Decimal(active_subscriptions)

        return PlatformDashboardResponse(
            total_businesses=total_businesses,
            active_businesses=active_businesses,
            suspended_businesses=suspended_businesses,
            archived_businesses=archived_businesses,
            total_accounts=total_accounts,
            active_subscriptions=active_subscriptions,
            expired_subscriptions=expired_subscriptions,
            mrr_idr=mrr_idr,
        )

    async def list_businesses(
        self,
        superadmin: UserInDB,
        status_filter: Optional[BusinessStatus] = None,
        search: Optional[str] = None,
    ) -> List[PlatformBusinessDetailResponse]:
        all_businesses = list(self.business_repo._businesses.values()) if hasattr(self.business_repo, "_businesses") else []
        
        if status_filter:
            all_businesses = [b for b in all_businesses if b.status == status_filter]
        if search:
            q = search.lower().strip()
            all_businesses = [b for b in all_businesses if q in b.name.lower() or q in b.slug.lower()]

        result = []
        for b in all_businesses:
            detail = await self._build_business_detail(b)
            result.append(detail)
        return result

    async def get_business_detail(self, superadmin: UserInDB, business_id: str) -> PlatformBusinessDetailResponse:
        business = await self.business_repo.get_by_id(business_id)
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found."
            )
        return await self._build_business_detail(business)

    async def _build_business_detail(self, b: BusinessInDB) -> PlatformBusinessDetailResponse:
        owner = await self.user_repo.get_by_id(b.owner_user_id)
        owner_email = owner.email if owner else None
        owner_name = owner.full_name if owner else None

        memberships = await self.membership_repo.list_by_business(b.id)
        branches = await self.branch_repo.list_by_business(b.id)
        sub = await self.sub_service.get_by_business_id(b.id)

        return PlatformBusinessDetailResponse(
            id=b.id,
            owner_user_id=b.owner_user_id,
            owner_email=owner_email,
            owner_name=owner_name,
            name=b.name,
            slug=b.slug,
            description=b.description,
            business_type=b.business_type,
            status=b.status,
            timezone=b.timezone,
            locale=b.locale,
            membership_count=len(memberships),
            branch_count=len(branches),
            created_at=b.created_at,
            updated_at=b.updated_at,
            subscription_status=sub.status.value if sub else None,
            subscription_plan_name=sub.plan_name if sub else None,
            subscription_current_period_end=sub.current_period_end if sub else None,
        )

    async def suspend_business(
        self, superadmin: UserInDB, business_id: str, action_input: BusinessActionInput
    ) -> PlatformBusinessDetailResponse:
        business = await self.business_repo.get_by_id(business_id)
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

        if business.status == BusinessStatus.SUSPENDED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business is already suspended.")
        if business.status == BusinessStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot suspend an archived business.")

        before_state = {"status": business.status.value, "name": business.name}
        
        # Update status
        business.status = BusinessStatus.SUSPENDED
        business.updated_at = datetime.now(timezone.utc)
        self.business_repo._businesses[business.id] = business

        after_state = {"status": business.status.value, "name": business.name}

        # Audit log
        await self.log_audit(
            actor=superadmin,
            action="BUSINESS_SUSPENDED",
            target_type="BUSINESS",
            target_id=business.id,
            target_business_id=business.id,
            reason=action_input.reason,
            before_state=before_state,
            after_state=after_state,
        )

        return await self._build_business_detail(business)

    async def activate_business(
        self, superadmin: UserInDB, business_id: str, action_input: BusinessActionInput
    ) -> PlatformBusinessDetailResponse:
        business = await self.business_repo.get_by_id(business_id)
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

        if business.status == BusinessStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business is already active.")
        if business.status == BusinessStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot activate an archived business.")

        before_state = {"status": business.status.value, "name": business.name}

        business.status = BusinessStatus.ACTIVE
        business.updated_at = datetime.now(timezone.utc)
        self.business_repo._businesses[business.id] = business

        after_state = {"status": business.status.value, "name": business.name}

        await self.log_audit(
            actor=superadmin,
            action="BUSINESS_ACTIVATED",
            target_type="BUSINESS",
            target_id=business.id,
            target_business_id=business.id,
            reason=action_input.reason,
            before_state=before_state,
            after_state=after_state,
        )

        return await self._build_business_detail(business)

    async def archive_business(
        self, superadmin: UserInDB, business_id: str, action_input: BusinessActionInput
    ) -> PlatformBusinessDetailResponse:
        business = await self.business_repo.get_by_id(business_id)
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

        if business.status == BusinessStatus.ARCHIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business is already archived.")

        before_state = {"status": business.status.value, "name": business.name}

        business.status = BusinessStatus.ARCHIVED
        business.updated_at = datetime.now(timezone.utc)
        self.business_repo._businesses[business.id] = business

        after_state = {"status": business.status.value, "name": business.name}

        await self.log_audit(
            actor=superadmin,
            action="BUSINESS_ARCHIVED",
            target_type="BUSINESS",
            target_id=business.id,
            target_business_id=business.id,
            reason=action_input.reason,
            before_state=before_state,
            after_state=after_state,
        )

        return await self._build_business_detail(business)

    async def list_business_members(self, superadmin: UserInDB, business_id: str):
        business = await self.business_repo.get_by_id(business_id)
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")
        
        memberships = await self.membership_repo.list_by_business(business_id)
        enriched = []
        for m in memberships:
            usr = await self.user_repo.get_by_id(m.user_id)
            enriched.append({
                "id": m.id,
                "business_id": m.business_id,
                "user_id": m.user_id,
                "role": m.role.value,
                "status": m.status.value,
                "email": usr.email if usr else None,
                "full_name": usr.full_name if usr else None,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            })
        return enriched

    async def list_users(
        self,
        superadmin: UserInDB,
        search: Optional[str] = None
    ) -> List[PlatformUserResponse]:
        users = await self.user_repo.list_all()
        if search:
            q = search.lower().strip()
            users = [u for u in users if q in u.email.lower() or q in u.full_name.lower()]
        return [PlatformUserResponse.model_validate(u) for u in users]

    async def list_audit_logs(
        self,
        superadmin: UserInDB,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[PlatformAuditLogResponse]:
        logs = await self.audit_repo.list_all(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            from_date=from_date,
            to_date=to_date,
        )
        return [PlatformAuditLogResponse.model_validate(l) for l in logs]

    async def override_subscription(
        self,
        superadmin: UserInDB,
        subscription_id: str,
        override_input: SubscriptionOverrideInput
    ) -> SubscriptionResponse:
        sub_before = await self.sub_service.get_by_id(subscription_id)
        if not sub_before:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")

        before_snapshot = {
            "status": sub_before.status.value,
            "current_period_end": sub_before.current_period_end.isoformat(),
            "price": str(sub_before.price),
            "currency": sub_before.currency,
        }

        updated_sub = await self.sub_service.override_subscription(subscription_id, override_input)

        after_snapshot = {
            "status": updated_sub.status.value,
            "current_period_end": updated_sub.current_period_end.isoformat(),
            "price": str(updated_sub.price),
            "currency": updated_sub.currency,
        }

        await self.log_audit(
            actor=superadmin,
            action="SUBSCRIPTION_OVERRIDE",
            target_type="SUBSCRIPTION",
            target_id=subscription_id,
            target_business_id=updated_sub.business_id,
            reason=override_input.reason,
            before_state=before_snapshot,
            after_state=after_snapshot,
            metadata={"action": override_input.action}
        )

        return SubscriptionResponse.model_validate(updated_sub)


platform_admin_service = PlatformAdminService()
