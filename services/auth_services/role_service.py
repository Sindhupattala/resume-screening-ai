from sqlalchemy.orm import Session
from fastapi import HTTPException
from db.models.auth_models import Role, Permission, UserRole, RolePermission, User
from schemas.auth_schemas import RoleCreate, PermissionCreate

class RoleService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_role(self, role: RoleCreate):
        db_role = self.db.query(Role).filter(Role.role_name == role.role_name).first()
        if db_role:
            raise HTTPException(status_code=400, detail="Role already exists")
        
        db_role = Role(role_name=role.role_name, description=role.description)
        self.db.add(db_role)
        self.db.commit()
        self.db.refresh(db_role)
        return db_role
    
    def create_permission(self, permission: PermissionCreate):
        db_permission = self.db.query(Permission).filter(
            Permission.permission_name == permission.permission_name
        ).first()
        if db_permission:
            raise HTTPException(status_code=400, detail="Permission already exists")
        
        db_permission = Permission(
            permission_name=permission.permission_name,
            description=permission.description
        )
        self.db.add(db_permission)
        self.db.commit()
        self.db.refresh(db_permission)
        return db_permission
    
    def assign_role_to_user(self, user_id: int, role_id: int):
        if not self.db.query(User).filter(User.user_id == user_id).first():
            raise HTTPException(status_code=404, detail="User not found")
        
        if not self.db.query(Role).filter(Role.role_id == role_id).first():
            raise HTTPException(status_code=404, detail="Role not found")
        
        if self.db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first():
            raise HTTPException(status_code=400, detail="Role already assigned to user")
        
        db_user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(db_user_role)
        self.db.commit()
        return {"message": "Role assigned to user"}
    
    def assign_permission_to_role(self, role_id: int, permission_id: int):
        if not self.db.query(Role).filter(Role.role_id == role_id).first():
            raise HTTPException(status_code=404, detail="Role not found")
        
        if not self.db.query(Permission).filter(Permission.permission_id == permission_id).first():
            raise HTTPException(status_code=404, detail="Permission not found")
        
        if self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        ).first():
            raise HTTPException(status_code=400, detail="Permission already assigned to role")
        
        db_role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
        self.db.add(db_role_permission)
        self.db.commit()
        return {"message": "Permission assigned to role"}