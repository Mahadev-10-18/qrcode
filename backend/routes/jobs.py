from fastapi import APIRouter, HTTPException, Response
import uuid
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from ..db import engine
from ..models import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/{job_id}")
async def get_job(job_id: uuid.UUID):
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Job).where(Job.id == job_id))
        job = result.one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status == "completed":
            return Response(
                content=job.result,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=sheet_{job.id}.pdf"}
            )
        return {"id": str(job.id), "status": job.status}
