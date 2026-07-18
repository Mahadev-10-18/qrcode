import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_free_user_limited_to_2_active_tags(client, user_a):
    """Free user can create 2 tags, 3rd is rejected with 403."""
    headers = {"X-User-Id": str(user_a.id)}

    # Tag 1 — should succeed
    r1 = await client.post("/tags/", json={"label": "Keys"}, headers=headers)
    assert r1.status_code == status.HTTP_201_CREATED

    # Tag 2 — should succeed
    r2 = await client.post("/tags/", json={"label": "Wallet"}, headers=headers)
    assert r2.status_code == status.HTTP_201_CREATED

    # Tag 3 — should be rejected
    r3 = await client.post("/tags/", json={"label": "Laptop"}, headers=headers)
    assert r3.status_code == status.HTTP_403_FORBIDDEN
    assert "Free plan is limited to 2 active tags" in r3.json()["detail"]
    assert "Upgrade" in r3.json()["detail"]


@pytest.mark.asyncio
async def test_free_user_pause_frees_slot(client, user_a):
    """Free user pauses one of 2 tags, can then create a new one."""
    headers = {"X-User-Id": str(user_a.id)}

    # Create 2 tags
    r1 = await client.post("/tags/", json={"label": "Keys"}, headers=headers)
    assert r1.status_code == status.HTTP_201_CREATED
    tag1_id = r1.json()["id"]

    r2 = await client.post("/tags/", json={"label": "Wallet"}, headers=headers)
    assert r2.status_code == status.HTTP_201_CREATED

    # Verify 3rd is blocked
    r3 = await client.post("/tags/", json={"label": "Laptop"}, headers=headers)
    assert r3.status_code == status.HTTP_403_FORBIDDEN

    # Pause tag 1
    patch_resp = await client.patch(
        f"/tags/{tag1_id}", json={"status": "paused"}, headers=headers
    )
    assert patch_resp.status_code == status.HTTP_200_OK

    # Now creating a 3rd tag should succeed — slot freed
    r4 = await client.post("/tags/", json={"label": "Laptop"}, headers=headers)
    assert r4.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_paid_user_unlimited_tags(client, paid_user):
    """Paid user can create more than 2 tags without hitting the limit."""
    headers = {"X-User-Id": str(paid_user.id)}

    for i in range(5):
        resp = await client.post(
            "/tags/", json={"label": f"Item {i}"}, headers=headers
        )
        assert resp.status_code == status.HTTP_201_CREATED, (
            f"Paid user blocked at tag {i + 1}: {resp.json()}"
        )
