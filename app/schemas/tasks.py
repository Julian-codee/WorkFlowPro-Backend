from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Título de la tarea")
    description: str | None = Field(None, description="Descripción detallada")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Prioridad")
    due_date: datetime | None = Field(None, description="Fecha límite (UTC)")
    assignee_id: UUID | None = Field(None, description="ID del usuario asignado")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    assignee_id: UUID | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus = Field(..., description="Nuevo estado de la tarea")


class TaskPriorityUpdate(BaseModel):
    priority: TaskPriority = Field(..., description="Nueva prioridad")


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: TaskStatus
    tenant_id: UUID
    created_by_id: UUID
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaskDeleteResponse(BaseModel):
    message: str = "Tarea eliminada correctamente"
    id: UUID