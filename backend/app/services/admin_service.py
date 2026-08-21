from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import \
(
    AdminPagination,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserRoleFilter,
)


class AdminService:
    @staticmethod
    def user_to_list_item\
    (
        user: User,
        active_engagements: int,
    ) -> AdminUserListItem:
        joined_date = user.created_at.date() if user.created_at else None

        #mvp user list from mock imagery
        return AdminUserListItem\
        (
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            joined_date=joined_date,
            active_engagements=active_engagements,
        )

    @staticmethod
    async def list_users\
    (
        db: AsyncSession,
        *,
        search: str | None,
        role: AdminUserRoleFilter | None,
        limit: int,
        offset: int,
    ) -> AdminUserListResponse:

        #role and search field mutations
        cleaned_search = search.strip() if search else None
        role_value = role.value if role else None

        rows, total = await AdminRepository.list_users\
        (
            db,
            search=cleaned_search,
            role=role_value,
            limit=limit,
            offset=offset,
        )

        #list number of engagements
        items = \
        [
            AdminService.user_to_list_item\
            (
                user,
                active_engagements=active_engagements,
            )
            for user, active_engagements in rows
        ]

        return AdminUserListResponse\
        (
            items=items,
            pagination=AdminPagination\
            (
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(items) < total,
            ),
        )