from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from schemas.auth_schemas import RoleCreate, PermissionCreate
from services.auth_services.role_service import RoleService
from db.session import get_db
from core.logging import TimeZoneLogger

logger = TimeZoneLogger().get_logger()



class RoleController:
    def __init__(self, router: APIRouter, db: Session = Depends(get_db)):
        self.router = router
        self.db_dependency = db  # Store dependency to use inside route handlers
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            '/roles',
            self.create_role,
            methods=['POST'],
            tags=['roles'],
            response_model=RoleCreate,
            summary="Create Role",
            description="Create a new role"
        )
        self.router.add_api_route(
            '/roles/permissions',
            self.create_permission,
            methods=['POST'],
            tags=['roles'],
            response_model=RoleCreate,
            summary="Create Permission",
            description="Create a new permission"
        )
        self.router.add_api_route(
            '/roles/users/{user_id}/roles/{role_id}',
            self.assign_role_to_user,
            methods=['POST'],
            tags=['roles'],
            response_model=RoleCreate,
            summary="Assign Role to User",
            description="Assign a role to a user"
        )
        self.router.add_api_route(
            '/roles/{role_id}/permissions/{permission_id}',
            self.assign_permission_to_role,
            methods=['POST'],
            tags=['roles'],
            response_model=PermissionCreate,
            summary="Assign Permission to Role",
            description="Assign a permission to a role"
        )

    def create_role(self, role: RoleCreate, db: Session = Depends(get_db)):
        try:
            service = RoleService(db)
            logger.info(f"Creating role: {role.name}")
            return service.create_role(role)
        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating role: {str(e)}")

    def create_permission(self, permission: PermissionCreate, db: Session = Depends(get_db)):
        try:
            service = RoleService(db)
            logger.info(f"Creating permission: {permission.name}")
            return service.create_permission(permission)
        except Exception as e:
            logger.error(f"Error creating permission: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating permission: {str(e)}")

    def assign_role_to_user(self, user_id: int, role_id: int, db: Session = Depends(get_db)):
        try:
            service = RoleService(db)
            logger.info(f"Assigning role ID {role_id} to user ID {user_id}")
            return service.assign_role_to_user(user_id, role_id)
        except ValueError as ve:
            logger.warning(str(ve))
            raise HTTPException(status_code=404, detail=str(ve))
        except Exception as e:
            logger.error(f"Error assigning role to user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    def assign_permission_to_role(self, role_id: int, permission_id: int, db: Session = Depends(get_db)):
        try:
            service = RoleService(db)
            logger.info(f"Assigning permission ID {permission_id} to role ID {role_id}")
            return service.assign_permission_to_role(role_id, permission_id)
        except ValueError as ve:
            logger.warning(str(ve))
            raise HTTPException(status_code=404, detail=str(ve))
        except Exception as e:
            logger.error(f"Error assigning permission to role: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")