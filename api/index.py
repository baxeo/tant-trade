from app.main import app as fastapi_app


class ApiPrefix:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/api"):
            scope = dict(scope)
            scope["path"] = scope["path"][4:] or "/"
            scope["raw_path"] = scope["path"].encode("utf-8")
        await self.application(scope, receive, send)


app = ApiPrefix(fastapi_app)