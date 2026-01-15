from fastapi import APIRouter, Body
from .services import UserService

router = APIRouter(prefix="/users", tags=["users"])
user_service = UserService()

@router.get("/{user_id}")
def get_user(user_id: int):
    return user_service.get_user(user_id)

@router.get("")
def list_users():
    return user_service.list_users()

@router.put("/profile/update")
def update_profile(data: dict = Body(...)):
    # simplistic extraction
    user_id = data.get("userId", 1)
    return user_service.update_profile(user_id, data)
