import pytest
from fastapi import status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import ValidationError

from backend.db import engine
from backend.models import User, Tag, ContactEvent, TagCreate, ContactRequest

@pytest.mark.asyncio
async def test_email_validation_error():
    # Attempting to construct User with invalid email should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate({"email": "invalid-email", "phone_number": "+15551234567"})
    assert "value is not a valid email address" in str(exc_info.value)


@pytest.mark.asyncio
async def test_phone_validation_error():
    # Attempting to construct User with invalid phone number should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate({"email": "test@example.com", "phone_number": "1234"})
    assert "Phone number must be in E.164 format" in str(exc_info.value)

    # Attempting to construct ContactRequest with invalid phone format should fail
    with pytest.raises(ValidationError) as exc_info:
        ContactRequest.model_validate({"method": "text", "finder_phone": "abc-123-xyz"})
    assert "Phone number must be in E.164 format" in str(exc_info.value)



@pytest.mark.asyncio
async def test_label_sanitization_and_render(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    
    # Submit tag with malicious label containing script tag
    malicious_label = "My keys <script>alert('XSS')</script>"
    resp = await client.post("/tags/", json={"label": malicious_label}, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED
    tag_id = resp.json()["id"]
    
    # Verify the script tag is escaped before storage (escaped value returned in JSON)
    escaped_label = "My keys &lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
    # Note: html.escape converts ' to &#x27; (or similar depending on python version)
    # Let's assert that it is escaped
    stored_label = resp.json()["label"]
    assert "<script>" not in stored_label
    assert "&lt;script&gt;" in stored_label

    # Verify the finder-facing page (Prompt 4 public view) renders it safely (returns escaped JSON)
    public_resp = await client.get(f"/t/{tag_id}")
    assert public_resp.status_code == status.HTTP_200_OK
    data = public_resp.json()
    assert data["label"] == stored_label
    # Ensure raw script tag is not present
    assert "<script>" not in public_resp.text
