import io
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
)
from app.modules.audit.events import AuditAction
from app.modules.audit.service import AuditLogService
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import UserLogin, UserRegister
from app.modules.auth.service import AuthService
from app.modules.billing.models import UpgradeRequest
from app.modules.billing.plans import PLANS_CONFIG, get_plan_limits
from app.modules.billing.schemas import UpgradeRequestCreate
from app.modules.billing.service import BillingService
from app.modules.demo.fixtures import DEMO_DEFAULT_PASSWORD
from app.modules.demo.service import DemoService
from app.modules.files.service import FileService
from app.modules.invitations.schemas import InvitationAccept, InvitationCreate
from app.modules.invitations.service import InvitationService
from app.modules.memberships.models import MembershipRole
from app.modules.memberships.service import MembershipService
from app.modules.organizations.models import Organization
from app.modules.organizations.schemas import OrganizationCreate
from app.modules.organizations.service import OrganizationService

@pytest.fixture(autouse=True)
def mock_jobs_in_coverage_tests():
    with patch("app.services.job_service.JobService.enqueue", return_value="mock-job-id"):
        yield


@pytest.mark.asyncio
async def test_billing_service_full_lifecycle(db_session: AsyncSession):
    service = BillingService(db_session)
    plans = await service.get_plans()
    assert len(plans) == 3
    plan_ids = {p.id for p in plans}
    assert plan_ids == {"free", "pro", "enterprise"}

    limits = BillingService.get_platform_limits()
    assert limits.deployment["tier"] == "zero-cost-free-tier"
    assert limits.compute_provider["memory_mb"] == 512

    # Create user & org
    auth_service = AuthService(db_session)
    user = await auth_service.register(UserRegister(email="billing_test@example.com", password="Password123!"))
    org_service = OrganizationService(db_session)
    org = await org_service.create_organization(user.id, OrganizationCreate(name="Billing Org"))

    # Entitlements
    entitlements = await service.get_entitlements(org.id)
    assert entitlements.plan == "free"
    assert entitlements.usage.members_count == 1
    assert entitlements.invites_remaining_this_hour == 5

    # Upgrade request
    req = await service.create_upgrade_request(
        org.id,
        user.id,
        UpgradeRequestCreate(requested_plan="pro", message="Need pro tier for team"),
    )
    assert req.status == "pending"
    assert req.requested_plan == "pro"

    # List upgrade requests
    all_reqs = await service.list_upgrade_requests()
    assert len(all_reqs) >= 1
    pending_reqs = await service.list_upgrade_requests(status="pending")
    assert any(r.id == req.id for r in pending_reqs)

    # Update org plan -> should auto-approve pending request
    updated_org = await service.update_organization_plan(org.id, "pro", user.id)
    assert updated_org.plan == "pro"

    req_after = await db_session.get(UpgradeRequest, req.id)
    assert req_after.status == "approved"

    # Entitlements after upgrade
    pro_entitlements = await service.get_entitlements(org.id)
    assert pro_entitlements.plan == "pro"
    assert pro_entitlements.limits.max_members == 50

    # Invalid plan error
    with pytest.raises(Exception):
        await service.update_organization_plan(org.id, "nonexistent_plan", user.id)

    # Nonexistent org error
    with pytest.raises(NotFoundError):
        await service.get_entitlements(uuid4())

    with pytest.raises(NotFoundError):
        await service.create_upgrade_request(uuid4(), user.id, UpgradeRequestCreate(requested_plan="pro"))

    with pytest.raises(NotFoundError):
        await service.update_organization_plan(uuid4(), "pro", user.id)


@pytest.mark.asyncio
async def test_demo_service_lazy_cleanup_and_limits(db_session: AsyncSession):
    service = DemoService(db_session)
    auth_service = AuthService(db_session)
    now = datetime.now(UTC)

    # 1. Create an expired demo user
    expired_user = await auth_service.register(UserRegister(email="expired_demo@demo.example.com", password="Password123!"))
    expired_user.is_demo = True
    expired_user.demo_expires_at = now - timedelta(hours=1)
    await db_session.commit()

    cleaned = await service.lazy_cleanup()
    assert cleaned >= 1

    user_check = await db_session.get(User, expired_user.id)
    assert user_check is None


@pytest.mark.asyncio
async def test_demo_upgrade_endpoint_errors(client: AsyncClient, db_session: AsyncSession):
    auth_service = AuthService(db_session)
    # Register real user
    real_user = await auth_service.register(UserRegister(email="real_user_upgrade@example.com", password="Password123!"))
    _, access_token, _, _ = await auth_service.login(UserLogin(email="real_user_upgrade@example.com", password="Password123!"))
    org = await OrganizationService(db_session).create_organization(real_user.id, OrganizationCreate(name="Real Org"))

    # Real user cannot use demo upgrade
    res = await client.post(
        "/demo/upgrade",
        headers={"Authorization": f"Bearer {access_token}", "X-Organization-Id": str(org.id)},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_invitation_service_edge_cases(db_session: AsyncSession):
    auth_service = AuthService(db_session)
    owner = await auth_service.register(UserRegister(email="inv_owner@example.com", password="Password123!"))
    member_user = await auth_service.register(UserRegister(email="inv_target@example.com", password="Password123!"))
    wrong_user = await auth_service.register(UserRegister(email="inv_wrong@example.com", password="Password123!"))

    org_service = OrganizationService(db_session)
    org = await org_service.create_organization(owner.id, OrganizationCreate(name="Inv Org"))

    inv_service = InvitationService(db_session)
    inv = await inv_service.create_invitation(
        inviter_id=owner.id,
        organization_id=org.id,
        data=InvitationCreate(email="inv_target@example.com"),
    )

    # List invitations
    invs = await inv_service.list_invitations(organization_id=org.id, actor_id=owner.id, status="pending")
    assert len(invs) == 1

    # Wrong user accept fails
    with pytest.raises(Exception):
        await inv_service.accept_invitation(
            user_id=wrong_user.id,
            user_email=wrong_user.email,
            data=InvitationAccept(token=inv.token),
        )

    # Valid accept
    accepted_inv = await inv_service.accept_invitation(
        user_id=member_user.id,
        user_email=member_user.email,
        data=InvitationAccept(token=inv.token),
    )
    assert accepted_inv.email == member_user.email

    # Double accept fails
    with pytest.raises(Exception):
        await inv_service.accept_invitation(
            user_id=member_user.id,
            user_email=member_user.email,
            data=InvitationAccept(token=inv.token),
        )

    # Create another invite and revoke it
    inv2 = await inv_service.create_invitation(
        inviter_id=owner.id,
        organization_id=org.id,
        data=InvitationCreate(email="inv_revoke@example.com"),
    )
    revoked = await inv_service.revoke_invitation(
        organization_id=org.id,
        invitation_id=inv2.id,
        actor_id=owner.id,
    )
    assert revoked.status == "revoked"


@pytest.mark.asyncio
async def test_organization_service_edge_cases(db_session: AsyncSession):
    auth_service = AuthService(db_session)
    owner = await auth_service.register(UserRegister(email="org_owner_test@example.com", password="Password123!"))
    org_service = OrganizationService(db_session)
    org = await org_service.create_organization(owner.id, OrganizationCreate(name="Org Edge Cases"))

    # Detail
    detail = await org_service.get_organization_detail(user_id=owner.id, organization_id=org.id)
    assert detail.role == "owner"
    assert detail.member_count == 1

    # List my orgs
    my_orgs = await org_service.list_user_organizations(owner.id)
    assert any(o.id == org.id and o.role == "owner" for o in my_orgs)

    # Owner cannot leave
    with pytest.raises(Exception):
        await org_service.leave_organization(org.id, owner.id)

    # Delete with wrong name
    with pytest.raises(Exception):
        await org_service.delete_organization(owner.id, org.id, confirmed_name="Wrong Name")

    # Delete successfully
    await org_service.delete_organization(owner.id, org.id, confirmed_name="Org Edge Cases")

    # Confirm deleted
    check = await org_service.repo.get_by_id(org.id)
    assert check is None


@pytest.mark.asyncio
async def test_auth_service_security_and_sessions(db_session: AsyncSession):
    auth_service = AuthService(db_session)
    user = await auth_service.register(UserRegister(email="security_test@example.com", password="Password123!"))

    # Test login
    user_res, token, refresh, session = await auth_service.login(
        UserLogin(email="security_test@example.com", password="Password123!"),
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
    )
    assert token is not None
    assert session is not None

    # Decode access token
    payload = decode_access_token(token)
    assert payload["sub"] == str(user.id)
    assert payload["sid"] == str(session.id)

    # Invalid token decode
    with pytest.raises(Exception):
        decode_access_token("invalid.token.here")

    # Change password errors
    with pytest.raises(Exception):
        # Wrong current password
        await auth_service.change_password(user.id, "WrongCurrentPwd!", "NewPassword123!")

    with pytest.raises(Exception):
        # Short new password
        await auth_service.change_password(user.id, "Password123!", "short")

    # Valid change password
    await auth_service.change_password(user.id, "Password123!", "NewPassword123!")

    # Verify new password works
    _, new_token, _, _ = await auth_service.login(
        UserLogin(email="security_test@example.com", password="NewPassword123!")
    )
    assert new_token is not None


@pytest.mark.asyncio
async def test_membership_service_management(db_session: AsyncSession):
    auth_service = AuthService(db_session)
    owner = await auth_service.register(UserRegister(email="mem_owner@example.com", password="Password123!"))
    member = await auth_service.register(UserRegister(email="mem_user@example.com", password="Password123!"))

    org_service = OrganizationService(db_session)
    org = await org_service.create_organization(owner.id, OrganizationCreate(name="Membership Org"))

    mem_service = MembershipService(db_session)
    # Add member
    membership = await mem_service.repo.create(
        user_id=member.id,
        organization_id=org.id,
        role=MembershipRole.MEMBER,
    )
    await db_session.commit()

    # Change role to admin
    updated_mem = await mem_service.change_role(
        requester_user_id=owner.id,
        organization_id=org.id,
        membership_id=membership.id,
        new_role=MembershipRole.ADMIN,
    )
    assert updated_mem.role == MembershipRole.ADMIN

    # Remove member
    await mem_service.remove_member(
        requester_user_id=owner.id,
        organization_id=org.id,
        membership_id=membership.id,
    )
    await db_session.commit()

    mem_check = await mem_service.repo.get_by_id(membership.id)
    assert mem_check is None


@pytest.mark.asyncio
async def test_file_service_crud_and_limits(db_session: AsyncSession):
    from fastapi import UploadFile

    auth_service = AuthService(db_session)
    user = await auth_service.register(UserRegister(email="files_test@example.com", password="Password123!"))
    org = await OrganizationService(db_session).create_organization(user.id, OrganizationCreate(name="Files Org"))

    file_service = FileService(db_session)

    # 1. Upload valid file
    stream = io.BytesIO(b"Hello from test file")
    upload = UploadFile(file=stream, filename="test.txt", headers={"content-type": "text/plain"})
    record = await file_service.upload_file(user_id=user.id, organization_id=org.id, upload=upload)
    assert record.file_name == "test.txt"
    assert record.file_size == len(b"Hello from test file")

    # 2. Get file
    fetched = await file_service.get_file(user_id=user.id, organization_id=org.id, file_id=record.id)
    assert fetched.id == record.id

    # 3. List files
    file_list = await file_service.list_files(user_id=user.id, organization_id=org.id)
    assert len(file_list) == 1

    # 4. Get statistics
    stats = await file_service.get_statistics(user_id=user.id, organization_id=org.id)
    assert stats["total_files"] == 1
    assert stats["total_size_bytes"] == len(b"Hello from test file")

    # 5. Download file
    content, name = await file_service.download_file(user_id=user.id, organization_id=org.id, file_id=record.id)
    assert content == b"Hello from test file"
    assert name == "test.txt"

    # 6. Delete file
    await file_service.delete_file(user_id=user.id, organization_id=org.id, file_id=record.id)
    with pytest.raises(NotFoundError):
        await file_service.get_file(user_id=user.id, organization_id=org.id, file_id=record.id)

    # 7. Upload empty file raises BadRequestError
    empty_stream = io.BytesIO(b"")
    empty_upload = UploadFile(file=empty_stream, filename="empty.txt")
    with pytest.raises(Exception):
        await file_service.upload_file(user_id=user.id, organization_id=org.id, upload=empty_upload)


@pytest.mark.asyncio
async def test_audit_service_export_and_sanitization(db_session: AsyncSession):
    from app.modules.audit.service import sanitize_csv_cell

    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd") == "'+cmd"
    assert sanitize_csv_cell("-calc") == "'-calc"
    assert sanitize_csv_cell("@sum") == "'@sum"
    assert sanitize_csv_cell("\tcmd") == "'\tcmd"
    assert sanitize_csv_cell("\rcmd") == "'\rcmd"
    assert sanitize_csv_cell("normal") == "normal"
    assert sanitize_csv_cell(None) == ""

    # Test export CSV stream
    auth_service = AuthService(db_session)
    user = await auth_service.register(UserRegister(email="audit_export@example.com", password="Password123!"))
    org = await OrganizationService(db_session).create_organization(user.id, OrganizationCreate(name="Audit Org"))

    audit_service = AuditLogService(db_session)
    await audit_service.create_event(
        organization_id=org.id,
        actor_user_id=user.id,
        action=AuditAction.ORGANIZATION_CREATED,
        resource_type="organization",
        resource_id=org.id,
        metadata={"test": "data"},
    )
    await db_session.commit()

    rows = []
    stream = await audit_service.export_events_csv(user.id, org.id)
    async for chunk in stream:
        rows.append(chunk)

    full_csv = "".join(rows)
    assert "id,created_at,action,actor_user_id,resource_type,resource_id,metadata" in full_csv
    assert "ORGANIZATION_CREATED" in full_csv

    # Test list events
    events, total = await audit_service.list_events(user.id, org.id, page=1, page_size=10)
    assert total >= 1
    assert any(e.action == AuditAction.ORGANIZATION_CREATED for e in events)


@pytest.mark.asyncio
async def test_demo_service_create_session_and_seed_script(db_session: AsyncSession):
    demo_service = DemoService(db_session)
    session_res = await demo_service.create_demo_session(members_count=1, files_count=1)
    assert session_res.access_token is not None
    assert session_res.organization_id is not None

    from uuid import UUID

    # Test demo upgrade to pro
    sub_uuid = UUID(decode_access_token(session_res.access_token)["sub"])
    owner_user = await UserRepository(db_session).get_by_id(sub_uuid)
    upgrade_res = await demo_service.upgrade_demo_organization(
        current_user=owner_user,
        organization_id=session_res.organization_id,
    )
    assert upgrade_res.plan == "pro"

    # Test seed_demo CLI script main()
    from app.scripts import seed_demo
    with patch("argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value.members = 1
        mock_args.return_value.files = 1
        await seed_demo.main()


@pytest.mark.asyncio
async def test_admin_billing_routes(client: AsyncClient, db_session: AsyncSession):
    # Register regular user and org
    auth_service = AuthService(db_session)
    user = await auth_service.register(UserRegister(email="reg_user@example.com", password="Password123!"))
    _, token, _, _ = await auth_service.login(UserLogin(email="reg_user@example.com", password="Password123!"))
    org = await OrganizationService(db_session).create_organization(user.id, OrganizationCreate(name="Admin Routes Org"))

    # Register platform admin
    admin = await auth_service.register(UserRegister(email="platform-admin@example.com", password="Password123!"))
    _, admin_token, _, _ = await auth_service.login(UserLogin(email="platform-admin@example.com", password="Password123!"))

    # User creates upgrade request
    res_req = await client.post(
        f"/organizations/{org.id}/upgrade-request",
        json={"requested_plan": "pro", "message": "Please upgrade us"},
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": str(org.id)},
    )
    assert res_req.status_code == 201

    # Admin lists upgrade requests
    res_list = await client.get(
        "/admin/upgrade-requests",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_list.status_code == 200
    assert any(r["requested_plan"] == "pro" for r in res_list.json())

    # Admin updates org plan
    res_patch = await client.patch(
        f"/admin/organizations/{org.id}/plan",
        json={"plan": "enterprise"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["plan"] == "enterprise"

    # Admin updates with invalid plan -> 400 or 422
    res_invalid = await client.patch(
        f"/admin/organizations/{org.id}/plan",
        json={"plan": "unsupported"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_invalid.status_code in (400, 422)
