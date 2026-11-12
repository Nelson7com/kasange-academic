from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Result, ResultStatus, Student
from schema import (
    ProfileSummary,
    ResultRead,
    StudentProfile,
    StudentRead,
    TeacherBrief,
)


async def build_student_profile(
    db: AsyncSession,
    student: Student,
    *,
    only_submitted: bool = False,
    term: int | None = None,
    year: int | None = None,
) -> StudentProfile:
    """Profile nzima: taarifa za mwanafunzi, mwalimu wake, matokeo na muhtasari."""
    stmt = (
        select(Result)
        .where(Result.student_id == student.id)
        .order_by(Result.year.desc(), Result.term, Result.subject)
    )
    if only_submitted:
        stmt = stmt.where(Result.status == ResultStatus.SUBMITTED)
    if term is not None:
        stmt = stmt.where(Result.term == term)
    if year is not None:
        stmt = stmt.where(Result.year == year)

    results = list((await db.execute(stmt)).scalars().all())
    marks = [r.marks for r in results]

    summary = ProfileSummary(
        total_results=len(results),
        average_marks=round(sum(marks) / len(marks), 2) if marks else None,
        draft_count=sum(r.status == ResultStatus.DRAFT for r in results),
        submitted_count=sum(r.status == ResultStatus.SUBMITTED for r in results),
    )
    return StudentProfile(
        student=StudentRead.model_validate(student),
        teacher=TeacherBrief.model_validate(student.teacher),
        results=[ResultRead.model_validate(r) for r in results],
        summary=summary,
    )