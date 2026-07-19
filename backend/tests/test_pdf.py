import pytest
from fastapi import status
from io import BytesIO


@pytest.mark.asyncio
async def test_pdf_sheet_one_page_for_three_tags(client, paid_user, auth_headers):
    """3 tags on a 6-per-page layout should produce exactly 1 PDF page."""
    headers = auth_headers(paid_user)
    tag_ids = []
    for label in ["One", "Two", "Three"]:
        resp = await client.post("/tags/", json={"label": label}, headers=headers)
        assert resp.status_code == status.HTTP_201_CREATED
        tag_ids.append(resp.json()["id"])

    resp = await client.post(
        "/tags/sheet", json={"tag_ids": tag_ids, "layout": 6}, headers=headers
    )
    assert resp.status_code == status.HTTP_200_OK
    job_id = resp.json()["job_id"]

    import asyncio
    completed = False
    pdf_content = b""
    for _ in range(10):
        poll_resp = await client.get(f"/jobs/{job_id}", headers=headers)
        if poll_resp.status_code == status.HTTP_200_OK and poll_resp.headers.get("content-type") == "application/pdf":
            pdf_content = poll_resp.content
            completed = True
            break
        await asyncio.sleep(0.5)

    assert completed is True
    from pdfminer.high_level import extract_pages

    page_count = sum(1 for _ in extract_pages(BytesIO(pdf_content)))
    assert page_count == 1, f"Expected 1 page, got {page_count}"


@pytest.mark.asyncio
async def test_owner_isolation_pdf_sheet(client, user_a, user_b, auth_headers):
    """User B cannot include User A's tag in a sheet — must get 404."""
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    resp = await client.post("/tags/", json={"label": "A Tag"}, headers=headers_a)
    assert resp.status_code == status.HTTP_201_CREATED
    tag_id = resp.json()["id"]

    resp2 = await client.post(
        "/tags/sheet", json={"tag_ids": [tag_id]}, headers=headers_b
    )
    assert resp2.status_code == status.HTTP_404_NOT_FOUND
