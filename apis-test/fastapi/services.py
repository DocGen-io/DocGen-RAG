from typing import List, Dict, Any

class AuthService:
    def login(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "token": "mock-jwt-token",
            "user": {"id": 1, "email": credentials.get("email")}
        }

    def signup(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": 2,
            **user_data
        }

class UserService:
    def get_user(self, user_id: int) -> Dict[str, Any]:
        return {"id": user_id, "name": "John Doe", "email": "john@example.com"}

    def list_users(self) -> List[Dict[str, Any]]:
        return [
            {"id": 1, "name": "John Doe"},
            {"id": 2, "name": "Jane Doe"}
        ]

    def update_profile(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": user_id, **data, "updated": True}
