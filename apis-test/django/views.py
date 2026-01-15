from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
from .services import AuthService, UserService

# Simulating DI
auth_service = AuthService()
user_service = UserService()

@method_decorator(csrf_exempt, name='dispatch')
class AuthLoginView(View):
    def post(self, request):
        data = json.loads(request.body)
        result = auth_service.login(data)
        return JsonResponse(result)

@method_decorator(csrf_exempt, name='dispatch')
class AuthSignupView(View):
    def post(self, request):
        data = json.loads(request.body)
        result = auth_service.signup(data)
        return JsonResponse(result)

class UserDetailView(View):
    def get(self, request, user_id):
        result = user_service.get_user(user_id)
        return JsonResponse(result)

class UserListView(View):
    def get(self, request):
        result = user_service.list_users()
        return JsonResponse(result, safe=False)

@method_decorator(csrf_exempt, name='dispatch')
class UserProfileUpdateView(View):
    def put(self, request):
        data = json.loads(request.body)
        # simplistic way to get ID
        user_id = data.get('userId', 1)
        result = user_service.update_profile(user_id, data)
        return JsonResponse(result)
