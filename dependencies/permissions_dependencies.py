from fastapi import Depends, HTTPException, status
from models import User
from dependencies.auth_dependencies import get_current_user
from models.enums import RoleEnum

# USER = 1
# MODERATOR = 2
# ADMIN = 3

def require_role(required_role: RoleEnum):

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role_level = current_user.role_id
        required_role_level = required_role.value

        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol '{required_role.name}' o superior."
            )

        return current_user

    return Depends(dependency)
