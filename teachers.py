from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_teacher
from grade import compute_grade
from models import Result, ResultStatus, Student, Teacher
from schema import (
    ResultCreate,
    ResultRead,
    ResultUpdate,
    StudentCreate,
    StudentProfile,
    StudentRead,
    StudentUpdate,
    SubmitRequest,
    SubmitResponse,
    TeacherRead,
    TeacherUpdate,
)
from service import build_student_profile

router = APIRouter(prefix="/teacher", tags=["Mwalimu"])


# ---------- Helpers ----------
async def _owned_student(db: AsyncSession, teacher: Teacher, student_id: int) -> Student:
    student = await db.get(Student, student_id)
    if student is None or student.teacher_id != teacher.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mwanafunzi hajapatikana")
    return student


async def _owned_result(db: AsyncSession, teacher: Teacher, result_id: int) -> Result:
    stmt = (
        select(Result)
        .join(Student, Result.student_id == Student.id)
        .where(Result.id == result_id, Student.teacher_id == teacher.id)
    )
    result = (await db.execute(stmt)).scalar_one_or_none()
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Matokeo hayajapatikana")
    return result


def _ensure_draft(result: Result) -> None:
    if result.status != ResultStatus.DRAFT:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Matokeo yameshatumwa kwa admin, hayawezi kubadilishwa",
        )


# ---------- Profile ya mwalimu ----------
@router.get("/me", response_model=TeacherRead)
async def get_me(teacher: Teacher = Depends(get_current_teacher)):
    return teacher


@router.patch("/me", response_model=TeacherRead)
async def update_me(
    data: TeacherUpdate,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field in ("full_name", "phone"):
            continue
        setattr(teacher, field, value)
    await db.flush()
    await db.refresh(teacher)
    return teacher


# ---------- Wanafunzi ----------
@router.post("/students", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
async def create_student(
    data: StudentCreate,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    student = Student(**data.model_dump(), teacher_id=teacher.id)
    db.add(student)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Namba ya usajili tayari ipo")
    await db.refresh(student)
    return student


@router.get("/students", response_model=list[StudentRead])
async def list_students(
    class_name: str | None = None,
    q: str | None = Query(default=None, description="Tafuta kwa jina au namba ya usajili"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Student).where(Student.teacher_id == teacher.id)
    if class_name:
        stmt = stmt.where(Student.class_name == class_name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Student.full_name.ilike(like), Student.admission_no.ilike(like)))
    stmt = stmt.order_by(Student.class_name, Student.full_name).offset(skip).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/students/{student_id}", response_model=StudentRead)
async def get_student(
    student_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    return await _owned_student(db, teacher, student_id)


@router.get("/students/{student_id}/profile", response_model=StudentProfile)
async def get_student_profile(
    student_id: int,
    term: int | None = Query(default=None, ge=1, le=3),
    year: int | None = None,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """Profile nzima: taarifa za mwanafunzi + matokeo yote (draft na yaliyotumwa) + muhtasari."""
    student = await _owned_student(db, teacher, student_id)
    return await build_student_profile(db, student, term=term, year=year)


@router.patch("/students/{student_id}", response_model=StudentRead)
async def update_student(
    student_id: int,
    data: StudentUpdate,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    student = await _owned_student(db, teacher, student_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field in ("admission_no", "full_name", "gender", "class_name"):
            continue
        setattr(student, field, value)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Namba ya usajili tayari ipo")
    await db.refresh(student)
    return student


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    student = await _owned_student(db, teacher, student_id)
    submitted = await db.scalar(
        select(func.count(Result.id)).where(
            Result.student_id == student.id, Result.status == ResultStatus.SUBMITTED
        )
    )
    if submitted:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Mwanafunzi ana matokeo yaliyotumwa kwa admin, hawezi kufutwa",
        )
    await db.execute(delete(Result).where(Result.student_id == student.id))
    await db.delete(student)


# ---------- Matokeo ----------
@router.post("/results", response_model=ResultRead, status_code=status.HTTP_201_CREATED)
async def create_result(
    data: ResultCreate,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    await _owned_student(db, teacher, data.student_id)
    result = Result(
        student_id=data.student_id,
        subject=data.subject.strip(),
        term=data.term,
        year=data.year,
        marks=data.marks,
        grade=compute_grade(data.marks),
        remarks=data.remarks,
        status=ResultStatus.DRAFT,
    )
    db.add(result)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Matokeo ya somo hili, muhula na mwaka huu tayari yapo kwa mwanafunzi huyu",
        )
    await db.refresh(result)
    return result


@router.get("/results", response_model=list[ResultRead])
async def list_results(
    student_id: int | None = None,
    term: int | None = Query(default=None, ge=1, le=3),
    year: int | None = None,
    result_status: str | None = Query(default=None, alias="status", pattern="^(draft|submitted)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Result)
        .join(Student, Result.student_id == Student.id)
        .where(Student.teacher_id == teacher.id)
    )
    if student_id is not None:
        stmt = stmt.where(Result.student_id == student_id)
    if term is not None:
        stmt = stmt.where(Result.term == term)
    if year is not None:
        stmt = stmt.where(Result.year == year)
    if result_status:
        stmt = stmt.where(Result.status == result_status)
    stmt = stmt.order_by(Result.year.desc(), Result.term, Result.subject).offset(skip).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.patch("/results/{result_id}", response_model=ResultRead)
async def update_result(
    result_id: int,
    data: ResultUpdate,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await _owned_result(db, teacher, result_id)
    _ensure_draft(result)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("marks") is not None:
        result.marks = changes["marks"]
        result.grade = compute_grade(result.marks)
    if "remarks" in changes:
        result.remarks = changes["remarks"]
    await db.flush()
    await db.refresh(result)
    return result


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(
    result_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await _owned_result(db, teacher, result_id)
    _ensure_draft(result)
    await db.delete(result)


@router.post("/results/submit", response_model=SubmitResponse)
async def submit_results(
    data: SubmitRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """Tuma kwa admin matokeo yote ya draft ya muhula na mwaka husika. Baada ya kutuma hayabadilishwi tena."""
    students = select(Student.id).where(Student.teacher_id == teacher.id)
    if data.class_name:
        students = students.where(Student.class_name == data.class_name)

    stmt = (
        update(Result)
        .where(
            Result.status == ResultStatus.DRAFT,
            Result.term == data.term,
            Result.year == data.year,
            Result.student_id.in_(students),
        )
        .values(status=ResultStatus.SUBMITTED, submitted_at=func.now())
        .execution_options(synchronize_session=False)
    )
    outcome = await db.execute(stmt)
    if outcome.rowcount == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Hakuna matokeo ya draft ya kutuma")
    return SubmitResponse(submitted=outcome.rowcount)