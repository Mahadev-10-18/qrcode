import pytest
import asyncio
from fastapi import status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db import engine
from backend.models import Tag, TagStatus, Job

@pytest.mark.asyncio
async def test_qr_caching_and_invalidation(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    
    # Create tag
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    tag_id = tag.id
    
    # First QR request: should be a MISS
    r1 = await client.get(f"/tags/{tag_id}/qr", headers=headers)
    assert r1.status_code == status.HTTP_200_OK
    assert r1.headers.get("X-Cache") == "MISS"
    
    # Second QR request: should be a HIT
    r2 = await client.get(f"/tags/{tag_id}/qr", headers=headers)
    assert r2.status_code == status.HTTP_200_OK
    assert r2.headers.get("X-Cache") == "HIT"
    
    # Update tag status (pause it) to trigger invalidation
    r_patch = await client.patch(f"/tags/{tag_id}", json={"status": TagStatus.PAUSED}, headers=headers)
    assert r_patch.status_code == status.HTTP_200_OK
    
    # Third QR request: should be a MISS again due to invalidation
    r3 = await client.get(f"/tags/{tag_id}/qr", headers=headers)
    assert r3.status_code == status.HTTP_200_OK
    assert r3.headers.get("X-Cache") == "MISS"


@pytest.mark.asyncio
async def test_pdf_sheet_async_generation(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    
    # Create 3 tags
    tag_ids = []
    async with AsyncSession(engine) as session:
        for i in range(3):
            tag = Tag(owner_id=user_a.id, label=f"Item {i}")
            session.add(tag)
            await session.commit()
            await session.refresh(tag)
            tag_ids.append(str(tag.id))
            
    # Submit sheet job
    response = await client.post("/tags/sheet", json={"tag_ids": tag_ids, "layout": 6}, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "job_id" in data
    assert data["status"] in ("pending", "processing", "completed")
    
    job_id = data["job_id"]
    
    # Poll job status
    completed = False
    for _ in range(10):  # poll up to 10 times
        poll_resp = await client.get(f"/jobs/{job_id}", headers=headers)
        if poll_resp.status_code == 200:
            if poll_resp.headers.get("content-type") == "application/pdf":
                completed = True
                assert len(poll_resp.content) > 0
                break
        await asyncio.sleep(0.5)
        
    assert completed is True
