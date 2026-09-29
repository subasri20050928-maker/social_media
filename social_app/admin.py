from django.contrib import admin
from .models import Profile, Post, Comment, Like, Follow


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'followers_count', 'following_count')
    search_fields = ('user__username', 'bio')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content_preview', 'created_at', 'likes_count', 'comments_count')
    search_fields = ('user__username', 'content')
    list_filter = ('created_at',)

    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'content_preview', 'created_at')
    search_fields = ('user__username', 'content')
    list_filter = ('created_at',)

    def content_preview(self, obj):
        return obj.content[:40] + ('...' if len(obj.content) > 40 else '')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'created_at')
    search_fields = ('user__username',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')
