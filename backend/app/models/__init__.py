"""ORM models. Importing this package registers every table on `Base.metadata`."""

from app.models.prediction import ModelVersion, Prediction
from app.models.student import Class, Intervention, MonthlyRecord, Student
from app.models.system import AuditLog, Setting
from app.models.user import RefreshToken, TeacherClass, User

__all__ = [
    "AuditLog",
    "Class",
    "Intervention",
    "ModelVersion",
    "MonthlyRecord",
    "Prediction",
    "RefreshToken",
    "Setting",
    "Student",
    "TeacherClass",
    "User",
]
