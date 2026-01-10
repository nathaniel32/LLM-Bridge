from fastapi import status, Request, Response, HTTPException, APIRouter
from fastapi.responses import FileResponse
import os
from server.setting import BASE_DIR
from pydantic import BaseModel
from jose import jwt, JWTError
import httpx
from datetime import datetime, timedelta, timezone

SECRET_KEY = os.getenv("JWT_SECRET", "M3DICOV3S*")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 1
LOGIN_API_URL = "https://v3s-python-2.3d-medico.com/login"

class TokenError(Exception):
    pass

class LoginRequest(BaseModel):
    username: str
    password: str

def access_token_validator(token: str):
    if not token:
        raise TokenError("Token not found")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise TokenError("Invalid token")
    except JWTError:
        raise TokenError("Invalid token or expired")
    return username

class Frontend:
    def __init__(self):
        self.router = APIRouter(tags=["Frontend"])
        self.router.add_api_route("/", self.root, methods=["GET"])
        self.router.add_api_route("/login", self.login, methods=["POST"])

    async def root(self, request: Request):
        token = request.cookies.get("access_token")
        try:
            access_token_validator(token)
            return FileResponse(os.path.join(BASE_DIR, ".frontend", "index.html"))
        except TokenError as e:
            return FileResponse(os.path.join(BASE_DIR, ".frontend", "auth.html"), status_code=status.HTTP_401_UNAUTHORIZED)
    
    async def login(self, response: Response, login_request: LoginRequest):
        try:
            async with httpx.AsyncClient() as client:
                api_response = await client.post(
                    LOGIN_API_URL,
                    json={"username": login_request.username, "password": login_request.password},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                data = api_response.json()
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"External API error: {str(e)}"
            )

        if api_response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=data.get("detail", "Login failed")
            )

        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {"sub": login_request.username, "exp": expire}
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=False, # dev mode
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        return {"message": "Login successful", "access_token": token}