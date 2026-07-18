import uuid
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_tag_uuid_randomness(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    r1 = await client.post("/tags/", json={"label": "first"}, headers=headers)
    r2 = await client.post("/tags/", json={"label": "second"}, headers=headers)
    assert r1.status_code == status.HTTP_201_CREATED
    assert r2.status_code == status.HTTP_201_CREATED
    id1 = uuid.UUID(r1.json()["id"])
    id2 = uuid.UUID(r2.json()["id"])
    assert id1.version == 4 and id2.version == 4
    # UUIDs are non-sequential — their integer values differ by more than 1
    assert abs(id1.int - id2.int) > 1


@pytest.mark.asyncio
async def test_user_isolation(client, user_a, user_b):
    headers_a = {"X-User-Id": str(user_a.id)}
    resp = await client.post("/tags/", json={"label": "A tag"}, headers=headers_a)
    assert resp.status_code == status.HTTP_201_CREATED
    tag_id = resp.json()["id"]

    # user B lists tags – should be empty
    headers_b = {"X-User-Id": str(user_b.id)}
    list_resp = await client.get("/tags/", headers=headers_b)
    assert list_resp.status_code == status.HTTP_200_OK
    assert list_resp.json() == []

    # user B patches A's tag – 404 (existence must not be leaked)
    patch_resp = await client.patch(
        f"/tags/{tag_id}", json={"label": "hacked"}, headers=headers_b
    )
    assert patch_resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_invalid_status_422(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    resp = await client.post("/tags/", json={"label": "valid"}, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED
    tag_id = resp.json()["id"]
    patch_resp = await client.patch(
        f"/tags/{tag_id}", json={"status": "not_valid"}, headers=headers
    )
    assert patch_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
