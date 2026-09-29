import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Prefetch

from .models import Profile, Post, Comment, Like, Follow
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    PostForm,
    CommentForm,
    ProfileEditForm
)


from django.contrib import messages


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data.get('email', '')
            password = form.cleaned_data['password']

            # Use create_user so the password is securely hashed
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            messages.success(request, "Registration successful! Please log in.")
            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            error = "Invalid username or password."
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('home')
            else:
                error = "Invalid username or password."

    return render(request, 'auth/login.html', {
        'error': error,
        'username': request.POST.get('username', '')
    })


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def feed_view(request):
    posts = Post.objects.select_related('user', 'user__profile').prefetch_related(
        'likes',
        Prefetch('comments', queryset=Comment.objects.select_related('user', 'user__profile'))
    ).all()

    # Pre-calculate liked post IDs for current user to avoid N+1 queries
    user_liked_post_ids = set(
        Like.objects.filter(user=request.user, post__in=posts).values_list('post_id', flat=True)
    )

    for post in posts:
        post.user_has_liked = post.id in user_liked_post_ids

    form = PostForm()
    return render(request, 'feed.html', {
        'posts': posts,
        'post_form': form,
    })


@login_required
@require_POST
def create_post_view(request):
    form = PostForm(request.POST)
    if form.is_valid():
        post = form.save(commit=False)
        post.user = request.user
        post.save()

        # Handle AJAX or standard form submission
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'post_id': post.id,
                'message': 'Post created successfully.'
            })
        return redirect('feed')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return redirect('feed')


@login_required
@require_POST
def delete_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.user != request.user:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'You can only delete your own posts.'}, status=403)
        return HttpResponseForbidden("You can only delete your own posts.")

    post.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Post deleted.'})
    return redirect('feed')


@login_required
@require_POST
def toggle_like_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like = Like.objects.filter(post=post, user=request.user).first()

    if like:
        like.delete()
        is_liked = False
    else:
        Like.objects.create(post=post, user=request.user)
        is_liked = True

    return JsonResponse({
        'success': True,
        'is_liked': is_liked,
        'likes_count': post.likes.count()
    })


@login_required
@require_POST
def toggle_follow_view(request, username):
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return JsonResponse({
            'success': False,
            'error': 'You cannot follow yourself.'
        }, status=400)

    follow = Follow.objects.filter(follower=request.user, following=target_user).first()

    if follow:
        follow.delete()
        is_following = False
    else:
        Follow.objects.create(follower=request.user, following=target_user)
        is_following = True

    return JsonResponse({
        'success': True,
        'is_following': is_following,
        'followers_count': target_user.followers_set.count(),
        'following_count': target_user.following_set.count()
    })


@login_required
@require_POST
def add_comment_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    content = ""

    # Support JSON payload or Form data
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    else:
        content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'success': False, 'error': 'Comment content cannot be empty.'}, status=400)

    comment = Comment.objects.create(
        post=post,
        user=request.user,
        content=content
    )

    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.id,
            'author': comment.user.username,
            'avatar_url': comment.user.profile.avatar_url,
            'content': comment.content,
            'created_at': comment.created_at.strftime('%b %d, %Y, %I:%M %p'),
            'can_delete': True
        },
        'comments_count': post.comments.count()
    })


@login_required
@require_POST
def delete_comment_view(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user:
        return JsonResponse({'success': False, 'error': 'You can only delete your own comments.'}, status=403)

    post = comment.post
    comment.delete()
    return JsonResponse({
        'success': True,
        'comments_count': post.comments.count()
    })


@login_required
def profile_view(request, username=None):
    if username is None or username == request.user.username:
        target_user = request.user
        is_own_profile = True
        is_following = False
    else:
        target_user = get_object_or_404(User, username=username)
        is_own_profile = False
        is_following = Follow.objects.filter(follower=request.user, following=target_user).exists()

    posts = target_user.posts.select_related('user', 'user__profile').prefetch_related(
        'likes',
        Prefetch('comments', queryset=Comment.objects.select_related('user', 'user__profile'))
    ).all()

    user_liked_post_ids = set(
        Like.objects.filter(user=request.user, post__in=posts).values_list('post_id', flat=True)
    )

    for post in posts:
        post.user_has_liked = post.id in user_liked_post_ids

    return render(request, 'profile.html', {
        'profile_user': target_user,
        'profile': target_user.profile,
        'is_own_profile': is_own_profile,
        'is_following': is_following,
        'posts': posts,
    })


@login_required
def edit_profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('my_profile')
    else:
        form = ProfileEditForm(instance=profile)

    return render(request, 'edit_profile.html', {'form': form})
