import os
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_qr_generation_and_decode(client, user_a, user_b):
    from backend.config import settings
    old_domain = settings.app_domain
    settings.app_domain = "http://mydomain.com"


    try:
        headers_a = {"X-User-Id": str(user_a.id)}
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
        headers_b = {"X-User-Id": str(user_b.id)}
        qr_resp_b = await client.get(f"/tags/{tag_id}/qr", headers=headers_b)
        assert qr_resp_b.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.app_domain = old_domain

