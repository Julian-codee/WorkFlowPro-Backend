from uuid import UUID

from app.db.session import AsyncSession
from app.models.tasks import TaskPriority, TaskStatus
from app.repositories.tasks import TaskRepository
from app.schemas.tasks import (
    TaskCreate,
    TaskListResponse,
    TaskPriorityUpdate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
import sqlalchemy as sa


class TaskService:
    def __init__(self, db: AsyncSession):
        self.repository = TaskRepository(db)
        self.db = db

    async def _get_current_user_id(self) -> UUID:
        """Obtener el user_id del contexto RLS."""
        result = await self.db.execute(
            sa.text("SELECT current_setting('app.current_user_id', true)")
        )
        user_id_str = result.scalar()
        return UUID(user_id_str)

    async def _get_current_tenant_id(self) -> UUID:
        """Obtener el tenant_id del contexto RLS."""
        result = await self.db.execute(
            sa.text("SELECT current_setting('app.current_tenant_id', true)")
        )
        tenant_id_str = result.scalar()
        return UUID(tenant_id_str)

    async def create_task(
        self,
        *,
        task_in: TaskCreate,
    ) -> TaskResponse:
        created_by_id = await self._get_current_user_id()
        tenant_id = await self._get_current_tenant_id()
        task = await self.repository.create(
            title=task_in.title,
            description=task_in.description,
            priority=task_in.priority,
            due_date=task_in.due_date,
            assignee_id=task_in.assignee_id,
            created_by_id=created_by_id,
            tenant_id=tenant_id,
        )
        return TaskResponse.model_validate(task)

    async def get_task(self, task_id: UUID) -> TaskResponse | None:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return None
        return TaskResponse.model_validate(task)

    async def get_tasks(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> TaskListResponse:
        tasks, total = await self.repository.get_all(
            page=page,
            page_size=page_size,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total + page_size - 1) // page_size

        return TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_task(
        self,
        task_id: UUID,
        task_in: TaskUpdate,
    ) -> TaskResponse | None:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return None

        updated_task = await self.repository.update(
            task,
            title=task_in.title,
            description=task_in.description,
            priority=task_in.priority,
            due_date=task_in.due_date,
            assignee_id=task_in.assignee_id,
        )
        return TaskResponse.model_validate(updated_task)

    async def update_task_status(
        self,
        task_id: UUID,
        status_in: TaskStatusUpdate,
    ) -> TaskResponse | None:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return None

        updated_task = await self.repository.update_status(task, status_in.status)
        return TaskResponse.model_validate(updated_task)

    async def update_task_priority(
        self,
        task_id: UUID,
        priority_in: TaskPriorityUpdate,
    ) -> TaskResponse | None:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return None

        updated_task = await self.repository.update_priority(task, priority_in.priority)
        return TaskResponse.model_validate(updated_task)

    async def delete_task(self, task_id: UUID) -> bool:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return False

        await self.repository.delete(task)
        return True