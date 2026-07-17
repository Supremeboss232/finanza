import pytest
from types import SimpleNamespace
from fastapi import HTTPException

import monitoring_service
from monitoring_service import AlertService
from rbac import require_permission


@pytest.mark.asyncio
async def test_rbac_admin_role_allows_transactions_create():
    user = SimpleNamespace(is_admin=False, admin_role="ADMIN")
    checker = require_permission("transactions:create")

    assert await checker(current_user=user) is True


@pytest.mark.asyncio
async def test_rbac_support_role_denies_kyc_review():
    user = SimpleNamespace(is_admin=False, role="support")
    checker = require_permission("kyc:review")

    with pytest.raises(HTTPException):
        await checker(current_user=user)


@pytest.mark.asyncio
async def test_alert_service_sends_email_alert(monkeypatch):
    sent = {}

    async def fake_send_email(subject, recipients, body, subtype="html"):
        sent["subject"] = subject
        sent["recipients"] = recipients
        sent["body"] = body
        sent["subtype"] = subtype
        return {"success": True}

    monkeypatch.setattr(monitoring_service.email_utils, "send_email", fake_send_email)

    result = await AlertService.send_email_alert(
        subject="Test Alert",
        message="Detail text",
        recipients=["ops@example.com"],
    )

    assert result["success"] is True
    assert sent["subject"] == "Test Alert"
    assert sent["recipients"] == ["ops@example.com"]
    assert "Detail text" in sent["body"]
    assert sent["subtype"] == "html"
