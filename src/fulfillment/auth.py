from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from .config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id or "not-configured",
    client_secret=settings.google_client_secret or "not-configured",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def oauth_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


@router.get("/login", name="auth_login")
async def login(request: Request):
    if not oauth_configured():
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_not_configured",
            status_code=307,
        )
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request):
    if not oauth_configured():
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_not_configured",
            status_code=307,
        )
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if not userinfo:
            userinfo = await oauth.google.userinfo(token=token)
        request.session["user"] = {
            "sub": userinfo.get("sub"),
            "name": userinfo.get("name") or userinfo.get("email"),
            "email": userinfo.get("email"),
            "picture": userinfo.get("picture"),
        }
        return RedirectResponse(url=settings.frontend_url, status_code=302)
    except Exception as exc:
        print(f"AUTH CALLBACK ERROR: {type(exc).__name__}: {exc}", flush=True)
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=authentication_failed",
            status_code=302,
        )


@router.get("/me")
async def current_user(request: Request):
    user = request.session.get("user")
    return {"authenticated": bool(user), "user": user}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out"}
