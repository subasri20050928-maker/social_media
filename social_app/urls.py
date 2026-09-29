from django.urls import path
from . import views

urlpatterns = [
    path('', views.feed_view, name='home'),
    path('feed/', views.feed_view, name='feed'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Post actions
    path('post/create/', views.create_post_view, name='create_post'),
    path('post/<int:post_id>/delete/', views.delete_post_view, name='delete_post'),
    path('post/<int:post_id>/like/', views.toggle_like_view, name='toggle_like'),
    path('post/<int:post_id>/comment/', views.add_comment_view, name='add_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment_view, name='delete_comment'),

    # Profile & Follow actions
    path('profile/', views.profile_view, name='my_profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/<str:username>/', views.profile_view, name='user_profile'),
    path('user/<str:username>/follow/', views.toggle_follow_view, name='toggle_follow'),
]
