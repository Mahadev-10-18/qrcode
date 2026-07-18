from fastapi import APIRouter, Depends, HTTPException, Response, status, BackgroundTasks
from typing import List
import uuid
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from pydantic import BaseModel
import asyncio
import logging

logger = logging.getLogger(__name__)

class SheetRequest(BaseModel):
    tag_ids: List[str]
    layout: int = 6

from ..auth_stub import get_current_user
from ..models import Tag, User, Job
from ..utils.pdf import render_grid_html, html_to_pdf
from ..db import engine

router = APIRouter(prefix="/tags", tags=["tags-pdf"])

async def generate_pdf_sheet_task(job_id: uuid.UUID, tag_ids: List[str], layout: int):
    tags: List[Tag] = []
    async with AsyncSession(engine) as session:
        # Load job
        job_result = await session.exec(select(Job).where(Job.id == job_id))
        job = job_result.one_or_none()
        if not job:
            return
            
        # Update job to processing
        job.status = "processing"
        session.add(job)
        await session.commit()
        
        try:
            for tid in tag_ids:
                tag_uuid = uuid.UUID(tid)
                result = await session.exec(select(Tag).where(Tag.id == tag_uuid))
                tag = result.one_or_none()
                if tag:
                    tags.append(tag)
                    
            if not tags:
                job.status = "failed"
                session.add(job)
                await session.commit()
                return
                
            # Render PDF sheet
            html = render_grid_html(tags, per_page=layout)
            pdf_bytes = await asyncio.to_thread(html_to_pdf, html)
            
            # Save result and complete job
            job.status = "completed"
            job.result = pdf_bytes
            session.add(job)
            await session.commit()
            logger.info(f"Background PDF sheet generation job {job_id} completed successfully.")
        except Exception as e:
            logger.error(f"Background PDF sheet job {job_id} failed: {e}", exc_info=True)
            job.status = "failed"
            session.add(job)
            await session.commit()


@router.get("/{tag_id}/pdf", response_class=Response)
async def get_tag_pdf(tag_id: str, current_user: User = Depends(get_current_user)):
    try:
        tag_uuid = uuid.UUID(tag_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == tag_uuid))
        tag = result.one_or_none()
        if not tag or tag.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
        html = render_grid_html([tag], per_page=1)
        pdf_bytes = html_to_pdf(html)
        return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/sheet")
async def post_tags_sheet(req: SheetRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    if req.layout not in (6, 12):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid layout")
        
    async with AsyncSession(engine) as session:
        # Validate that the user owns all tag_ids first
        for tid in req.tag_ids:
            try:
                tag_uuid = uuid.UUID(tid)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
            result = await session.exec(select(Tag).where(Tag.id == tag_uuid))
            tag = result.one_or_none()
            if not tag or tag.owner_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
                
        # Create Job record
        job = Job(status="pending")
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        # Enqueue background task
        background_tasks.add_task(generate_pdf_sheet_task, job.id, req.tag_ids, req.layout)
        
        return {"job_id": str(job.id), "status": job.status}

