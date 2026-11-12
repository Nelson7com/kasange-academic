from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=72)


# ---------- Mwalimu ----------
class TeacherCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=100)
    employee_no: str | None = Field(default=None, max_length=30)


class TeacherUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=100)


class AdminTeacherUpdate(TeacherUpdate):
    is_active: bool | None = None


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str
    address: str | None
    subject: str | None
    employee_no: str | None
    is_active: bool
    created_at: datetime


class TeacherDetail(TeacherRead):
    students_count: int = 0


class TeacherBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str


# ---------- Mwanafunzi ----------
Gender = Literal["M", "F"]


class StudentCreate(BaseModel):
    admission_no: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=2, max_length=100)
    gender: Gender
    date_of_birth: date | None = None
    class_name: str = Field(min_length=1, max_length=30)
    guardian_name: str | None = Field(default=None, max_length=100)
    guardian_phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)


class StudentUpdate(BaseModel):
    admission_no: str | None = Field(default=None, min_length=1, max_length=30)
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    gender: Gender | None = None
    date_of_birth: date | None = None
    class_name: str | None = Field(default=None, min_length=1, max_length=30)
    guardian_name: str | None = Field(default=None, max_length=100)
    guardian_phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    admission_no: str
    full_name: str
    gender: str
    date_of_birth: date | None
    class_name: str
    guardian_name: str | None
    guardian_phone: str | None
    address: str | None
    created_at: datetime


# ---------- Matokeo ----------
class ResultCreate(BaseModel):
    student_id: int
    subject: str = Field(min_length=1, max_length=60)
    term: int = Field(ge=1, le=3)
    year: int = Field(ge=2000, le=2100)
    marks: float = Field(ge=0, le=100)
    remarks: str | None = Field(default=None, max_length=255)


class ResultUpdate(BaseModel):
    marks: float | None = Field(default=None, ge=0, le=100)
    remarks: str | None = Field(default=None, max_length=255)


class ResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    subject: str
    term: int
    year: int
    marks: float
    grade: str
    remarks: str | None
    status: str
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResultAdminRead(ResultRead):
    student_name: str
    admission_no: str
    class_name: str
    teacher_id: int
    teacher_name: str


class SubmitRequest(BaseModel):
    term: int = Field(ge=1, le=3)
    year: int = Field(ge=2000, le=2100)
    class_name: str | None = None  # kama ni tupu, anatuma madarasa yake yote


class SubmitResponse(BaseModel):
    submitted: int


# ---------- Profile ya mwanafunzi ----------
class ProfileSummary(BaseModel):
    total_results: int
    average_marks: float | None
    draft_count: int
    submitted_count: int


class StudentProfile(BaseModel):
    student: StudentRead
    teacher: TeacherBrief
    results: list[ResultRead]
    summary: ProfileSummary