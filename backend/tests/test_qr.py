import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_qr_generation_and_decode(client, user_a, user_b, auth_headers):
    from backend.config import settings
    old_frontend = settings.frontend_url
    old_qr_base = settings.qr_base_url
    settings.frontend_url = "http://mydomain.com"
    settings.qr_base_url = ""

    try:
        headers_a = auth_headers(user_a)
        resp = await client.post("/tags/", json={"label": "my tag"}, headers=headers_a)
        assert resp.status_code == status.HTTP_201_CREATED
        tag_id = resp.json()["id"]

        # Fetch QR PNG
        qr_resp = await client.get(f"/tags/{tag_id}/qr", headers=headers_a)
        assert qr_resp.status_code == status.HTTP_200_OK
        assert qr_resp.headers["content-type"] == "image/png"
        img_bytes = qr_resp.content

        # Decode QR using OpenCV
        import cv2
        import numpy as np

        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        decoded, points, _ = detector.detectAndDecode(img)
        assert decoded == f"http://mydomain.com/t/{tag_id}", (
            f"Decoded '{decoded}' != expected URL"
        )

        # Non-owner gets 404
        headers_b = auth_headers(user_b)
        qr_resp_b = await client.get(f"/tags/{tag_id}/qr", headers=headers_b)
        assert qr_resp_b.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.frontend_url = old_frontend
        settings.qr_base_url = old_qr_base
