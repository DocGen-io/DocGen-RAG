from fastapi import APIRouter, Body
from .services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()

@router.post("/login")
def login(credentials: dict = Body(...)):
    return auth_service.login(credentials)

@router.post("/signup")
def signup(user_data: dict = Body(...)):
    return auth_service.signup(user_data)
