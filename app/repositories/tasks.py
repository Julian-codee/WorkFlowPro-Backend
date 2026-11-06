from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tasks import Task, TaskPriority, TaskStatus


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        title: str,
        created_by_id: UUID,
        tenant_id: UUID,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: datetime | None = None,
        assignee_id: UUID | None = None,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            assignee_id=assignee_id,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID) -> Task | None:
        stmt = select(Task).where(Task.id == task_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
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
    ) -> tuple[Sequence[Task], int]:
        stmt = select(Task)
        count_stmt = select(func.count())

        # Filters
        if status:
            stmt = stmt.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
            count_stmt = count_stmt.where(Task.priority == priority)
        if assignee_id:
            stmt = stmt.where(Task.assignee_id == assignee_id)
            count_stmt = count_stmt.where(Task.assignee_id == assignee_id)
        if search:
            search_filter = or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Sorting
        sort_column = getattr(Task, sort_by, Task.created_at)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Execute
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return tasks, total

    async def update(
        self,
        task: Task,
        *,
        title: str | None = None,
        description: str | None = None,
        priority: TaskPriority | None = None,
        due_date: datetime | None = None,
        assignee_id: UUID | None = None,
    ) -> Task:
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if due_date is not None:
            task.due_date = due_date
        if assignee_id is not None:
            task.assignee_id = assignee_id

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def update_status(self, task: Task, status: TaskStatus) -> Task:
        task.status = status
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        else:
            task.completed_at = None

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def update_priority(self, task: Task, priority: TaskPriority) -> Task:
        task.priority = priority
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.db.delete(task)
        await self.db.flush()