from django.urls import path
from .views import (
    AuthLoginView, 
    AuthSignupView, 
    UserDetailView, 
    UserListView, 
    UserProfileUpdateView
)

urlpatterns = [
    path('auth/login', AuthLoginView.as_view(), name='auth_login'),
    path('auth/signup', AuthSignupView.as_view(), name='auth_signup'),
    path('users/<int:user_id>', UserDetailView.as_view(), name='user_detail'),
    path('users', UserListView.as_view(), name='user_list'),
    path('users/profile/update', UserProfileUpdateView.as_view(), name='user_profile_update'),
]
