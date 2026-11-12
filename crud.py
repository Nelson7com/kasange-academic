from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Student
from schema import StudentCreate, StudentUpdate

# Kumbuka: get_db() ndiyo inafanya commit, kwa hiyo hapa tunatumia flush() tu.


async def create_student(db: AsyncSession, data: StudentCreate) -> Student:
    student = Student(**data.model_dump())
    db.add(student)
    await db.flush()
    await db.refresh(student)
    return student


async def get_student(db: AsyncSession, student_id: int) -> Student | None:
    return await db.get(Student, student_id)


async def list_students(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Student]:
    result = await db.execute(
        select(Student).order_by(Student.id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def update_student(
    db: AsyncSession, student: Student, data: StudentUpdate
) -> Student:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    await db.flush()
    await db.refresh(student)
    return student


async def delete_student(db: AsyncSession, student: Student) -> None:
    await db.delete(student)
    await db.flush()