from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from routes.auth_routes.auth_routes import AuthController
from routes.auth_routes.roles_routes import RoleController
from routes.auth_routes.auth_ui_routes import AuthUIRouter
from routes.resume_screening_routes import ResumeScreeningController
# Set up templates directory
templates = Jinja2Templates(directory="templates")
router=APIRouter()

#####################################
# Authentication
#####################################

AuthController(router=router)
RoleController(router=router)
AuthUIRouter(router=router,templates=templates)
ResumeScreeningController(router=router)