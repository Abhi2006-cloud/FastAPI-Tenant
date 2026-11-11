import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_change_password_flow_and_revocation(client: AsyncClient):
    """G7: Test change-password validation, session revocation, and login with new password."""
    email = "pwdchange@example.com"
    old_pwd = "OldPassword123!"
    new_pwd = "NewSecurePassword456!"

    # 1. Register & login
    await client.post("/auth/register", json={"email": email, "password": old_pwd})
    login_res = await client.post("/auth/login", json={"email": email, "password": old_pwd})
    assert login_res.status_code == 200
    old_access_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {old_access_token}"}

    # 2. Incorrect current password -> 400
    res_wrong_cur = await client.post(
        "/auth/change-password",
        json={"current_password": "WrongOldPassword!", "new_password": new_pwd},
        headers=headers,
    )
    assert res_wrong_cur.status_code == 400
    assert "Current password is incorrect" in res_wrong_cur.text

    # 3. New password too short -> 422
    res_too_short = await client.post(
        "/auth/change-password",
        json={"current_password": old_pwd, "new_password": "short"},
        headers=headers,
    )
    assert res_too_short.status_code == 422

    # 4. Successful password change -> 204
    res_ok = await client.post(
        "/auth/change-password",
        json={"current_password": old_pwd, "new_password": new_pwd},
        headers=headers,
    )
    assert res_ok.status_code == 204

    # 5. Old access token is now revoked -> 401
    res_old_token = await client.get("/auth/me", headers=headers)
    assert res_old_token.status_code == 401

    # 6. Login with old password fails -> 401
    res_old_login = await client.post("/auth/login", json={"email": email, "password": old_pwd})
    assert res_old_login.status_code == 401

    # 7. Login with new password succeeds -> 200
    res_new_login = await client.post("/auth/login", json={"email": email, "password": new_pwd})
    assert res_new_login.status_code == 200
    assert "access_token" in res_new_login.json()
