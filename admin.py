from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_admin
from models import Result, ResultStatus, Role, Student, Teacher, User
from schema import (
    AdminTeacherUpdate,
    ResultAdminRead,
    ResultRead,
    StudentProfile,
    StudentRead,
    TeacherCreate,
    TeacherDetail,
    TeacherRead,
)
from security import hash_password
from service import build_student_profile

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin)],
)


# ---------- Walimu ----------
@router.post("/teachers", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
async def create_teacher(data: TeacherCreate, db: AsyncSession = Depends(get_db)):
    """Admin anatengeneza akaunti ya mwalimu pamoja na taarifa zake."""
    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        role=Role.TEACHER,
    )
    teacher = Teacher(
        user=user,
        full_name=data.full_name,
        phone=data.phone,
        address=data.address,
        subject=data.subject,
        employee_no=data.employee_no,
    )
    db.add(teacher)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Email au namba ya mfanyakazi tayari imetumika"
        )
    await db.refresh(teacher)
    return teacher


@router.get("/teachers", response_model=list[TeacherRead])
async def list_teachers(
    q: str | None = Query(default=None, description="Tafuta kwa jina, simu au namba ya mfanyakazi"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Teacher)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Teacher.full_name.ilike(like),
                Teacher.phone.ilike(like),
                Teacher.employee_no.ilike(like),
            )
        )
    stmt = stmt.order_by(Teacher.full_name).offset(skip).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/teachers/{teacher_id}", response_model=TeacherDetail)
async def get_teacher(teacher_id: int, db: AsyncSession = Depends(get_db)):
    teacher = await db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mwalimu hajapatikana")
    detail = TeacherDetail.model_validate(teacher)
    detail.students_count = (
        await db.scalar(select(func.count(Student.id)).where(Student.teacher_id == teacher_id))
    ) or 0
    return detail


@router.patch("/teachers/{teacher_id}", response_model=TeacherRead)
async def update_teacher(
    teacher_id: int, data: AdminTeacherUpdate, db: AsyncSession = Depends(get_db)
):
    """Hariri taarifa za mwalimu au zima/washa akaunti yake (`is_active`)."""
    teacher = await db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mwalimu hajapatikana")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_active") is not None:
        teacher.user.is_active = changes["is_active"]
    for field in ("full_name", "phone", "address", "subject"):
        if field in changes and not (changes[field] is None and field in ("full_name", "phone")):
            setattr(teacher, field, changes[field])
    await db.flush()
    await db.refresh(teacher)
    return teacher


# ---------- Wanafunzi (angalia tu) ----------
@router.get("/students", response_model=list[StudentRead])
async def list_students(
    teacher_id: int | None = None,
    class_name: str | None = None,
    q: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Student)
    if teacher_id is not None:
        stmt = stmt.where(Student.teacher_id == teacher_id)
    if class_name:
        stmt = stmt.where(Student.class_name == class_name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Student.full_name.ilike(like), Student.admission_no.ilike(like)))
    stmt = stmt.order_by(Student.class_name, Student.full_name).offset(skip).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/students/{student_id}/profile", response_model=StudentProfile)
async def get_student_profile(
    student_id: int,
    term: int | None = Query(default=None, ge=1, le=3),
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Profile ya mwanafunzi na matokeo yaliyotumwa na mwalimu tu."""
    student = await db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mwanafunzi hajapatikana")
    return await build_student_profile(
        db, student, only_submitted=True, term=term, year=year
    )


# ---------- Matokeo yaliyotumwa ----------
@router.get("/results", response_model=list[ResultAdminRead])
async def list_submitted_results(
    teacher_id: int | None = None,
    student_id: int | None = None,
    class_name: str | None = None,
    subject: str | None = None,
    term: int | None = Query(default=None, ge=1, le=3),
    year: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Matokeo yote yaliyotumwa na walimu (draft hazionekani kwa admin)."""
    stmt = (
        select(Result, Student, Teacher)
        .join(Student, Result.student_id == Student.id)
        .join(Teacher, Student.teacher_id == Teacher.id)
        .where(Result.status == ResultStatus.SUBMITTED)
    )
    if teacher_id is not None:
        stmt = stmt.where(Teacher.id == teacher_id)
    if student_id is not None:
        stmt = stmt.where(Student.id == student_id)
    if class_name:
        stmt = stmt.where(Student.class_name == class_name)
    if subject:
        stmt = stmt.where(Result.subject.ilike(subject))
    if term is not None:
        stmt = stmt.where(Result.term == term)
    if year is not None:
        stmt = stmt.where(Result.year == year)
    stmt = (
        stmt.order_by(
            Result.year.desc(), Result.term, Student.class_name, Student.full_name, Result.subject
        )
        .offset(skip)
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()
    return [
        ResultAdminRead(
            **ResultRead.model_validate(result).model_dump(),
            student_name=student.full_name,
            admission_no=student.admission_no,
            class_name=student.class_name,
            teacher_id=teacher.id,
            teacher_name=teacher.full_name,
        )
        for result, student, teacher in rows
    ]