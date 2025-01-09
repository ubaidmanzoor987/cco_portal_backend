from django.urls import include, path
from .views import (
    UserSignupView,
    UserLoginView,
    UserLogoutView,
    FBGetCurrentUserView, UserUpdateView, UserDeleteView, UserListView, UserDetailView, LoginView,
    ResetPasswordAPIView
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path("users/signup/", UserSignupView.as_view(), name="user-signup"),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/update/<int:pk>/', UserUpdateView.as_view(), name='user-update'),
    path('users/delete/<int:user_id>/', UserDeleteView.as_view(), name='user-delete'),
    path("account/login/", UserLoginView.as_view(), name="user-login"),
    path("account/cco_login/", LoginView.as_view({'post': 'login_CCO'}), name="cco-login"),
    path('account/login/fiduciary/', LoginView.as_view({'post': 'login_fiduciary'}), name='login_fiduciary'),
    path("account/logout/", UserLogoutView.as_view(), name="user-logout"),
    path("current_user/", FBGetCurrentUserView.as_view(), name="current-user"),
    path('account/password/reset/', ResetPasswordAPIView.as_view(), name='reset-password'),
]
