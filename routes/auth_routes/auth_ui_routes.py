from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates



class AuthUIRouter:
    def __init__(self, router: APIRouter, templates: Jinja2Templates):
        self.router = router
        self.templates = templates

        self.router.add_api_route(
            '/',
            self.login,
            methods=['GET'],
            tags=['LOGIN UI']
        )
        self.router.add_api_route(
            '/ui/dashboard',
            self.dashboard,
            methods=['GET'],
            tags=['DashBoard']
        )
        self.router.add_api_route(
            '/ui/signup',
            self.register,
            methods=['GET'],
            tags=['Register']
        )


    async def register(self,request:Request):
        return self.templates.TemplateResponse(
            name='auth/register.html',
            context={'request':request}
        )

    async def login(self, request: Request):
        return self.templates.TemplateResponse(
            name='auth/index.html',
            context={'request': request}
        )
    async def dashboard(self, request:Request):
        return self.templates.TemplateResponse(
            name='Home.html',
            context={'request':request}
        )
