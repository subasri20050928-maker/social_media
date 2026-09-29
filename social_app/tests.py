from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import Profile, Post, Comment, Like, Follow


class MiniSocialPlatformTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test users with create_user to ensure proper password hashing
        self.user1 = User.objects.create_user(username='alice', password='password123', email='alice@example.com')
        self.user2 = User.objects.create_user(username='bob', password='password123', email='bob@example.com')

    def test_profile_auto_created_signal(self):
        """Test that Profile is automatically created on user creation via post_save signal."""
        self.assertIsNotNone(self.user1.profile)
        self.assertEqual(self.user1.profile.user.username, 'alice')
        self.assertEqual(self.user1.profile.followers_count, 0)
        self.assertEqual(self.user1.profile.following_count, 0)

    def test_user_registration_flow(self):
        """Test user registration endpoint creates user with hashed password, saves to DB, and redirects to login."""
        response = self.client.post(reverse('register'), {
            'username': 'charlie',
            'email': 'charlie@example.com',
            'password': 'password123',
            'password_confirm': 'password123'
        })
        # Should redirect to login page
        self.assertRedirects(response, reverse('login'))

        # Verify user is saved in database and password is encrypted (not plain text)
        user = User.objects.filter(username='charlie').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('password123'))
        self.assertNotEqual(user.password, 'password123')
        self.assertIsNotNone(user.profile)

    def test_login_success(self):
        """Test login with correct credentials creates session and redirects to home/feed displaying username."""
        response = self.client.post(reverse('login'), {
            'username': 'alice',
            'password': 'password123'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].username, 'alice')
        self.assertContains(response, '@alice')

    def test_login_invalid_username(self):
        """Test login with non-existent username displays error message and stays on login page."""
        response = self.client.post(reverse('login'), {
            'username': 'nonexistent_user',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password.")
        self.assertFalse(response.context['user'].is_authenticated)

    def test_login_invalid_password(self):
        """Test login with existing user but wrong password displays error message and stays on login page."""
        response = self.client.post(reverse('login'), {
            'username': 'alice',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password.")
        self.assertFalse(response.context['user'].is_authenticated)

    def test_logout_destroys_session(self):
        """Test logout clears session and redirects to login."""
        self.client.login(username='alice', password='password123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

        # Subsequent request should show user is anonymous
        feed_response = self.client.get(reverse('home'))
        self.assertRedirects(feed_response, f"{reverse('login')}?next=/")

    def test_protected_pages_blocked_for_unauthenticated_user(self):
        """Unauthenticated users cannot access feed, post creation, profile, or actions."""
        # Feed/Home
        res_feed = self.client.get(reverse('home'))
        self.assertRedirects(res_feed, f"{reverse('login')}?next=/")

        # Create post
        res_create = self.client.post(reverse('create_post'), {'content': 'Hacking feed'})
        self.assertRedirects(res_create, f"{reverse('login')}?next={reverse('create_post')}")

        # Profile
        res_profile = self.client.get(reverse('my_profile'))
        self.assertRedirects(res_profile, f"{reverse('login')}?next={reverse('my_profile')}")

        # Follow action
        res_follow = self.client.post(reverse('toggle_follow', args=['alice']))
        self.assertRedirects(res_follow, f"{reverse('login')}?next={reverse('toggle_follow', args=['alice'])}")

    def test_post_creation_and_ordering(self):
        """Test creating posts and ensuring reverse chronological order."""
        post1 = Post.objects.create(user=self.user1, content="Alice's first post")
        post2 = Post.objects.create(user=self.user1, content="Alice's second post")

        posts = list(Post.objects.all())
        self.assertEqual(posts[0].id, post2.id)
        self.assertEqual(posts[1].id, post1.id)

    def test_delete_own_post_and_forbidden_for_others(self):
        """Test that users can only delete their own posts."""
        post = Post.objects.create(user=self.user1, content="Alice post to delete")

        # Bob attempts to delete Alice's post
        self.client.login(username='bob', password='password123')
        forbidden_response = self.client.post(reverse('delete_post', args=[post.id]))
        self.assertEqual(forbidden_response.status_code, 403)
        self.assertTrue(Post.objects.filter(id=post.id).exists())

        # Alice deletes her own post
        self.client.login(username='alice', password='password123')
        delete_response = self.client.post(reverse('delete_post', args=[post.id]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Post.objects.filter(id=post.id).exists())

    def test_like_toggle_and_duplicate_prevention(self):
        """Test like/unlike AJAX endpoint and duplicate like constraint."""
        post = Post.objects.create(user=self.user1, content="Likeable post")
        self.client.login(username='bob', password='password123')

        # 1. Like
        res1 = self.client.post(reverse('toggle_like', args=[post.id]))
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1['is_liked'])
        self.assertEqual(data1['likes_count'], 1)

        # 2. Unlike
        res2 = self.client.post(reverse('toggle_like', args=[post.id]))
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertFalse(data2['is_liked'])
        self.assertEqual(data2['likes_count'], 0)

        # 3. Model duplicate constraint
        Like.objects.create(user=self.user2, post=post)
        with self.assertRaises(Exception):
            Like.objects.create(user=self.user2, post=post)

    def test_follow_toggle_and_self_follow_prevention(self):
        """Test follow/unfollow AJAX endpoint and self-follow validation."""
        self.client.login(username='bob', password='password123')

        # Bob follows Alice
        res1 = self.client.post(reverse('toggle_follow', args=['alice']))
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1['is_following'])
        self.assertEqual(data1['followers_count'], 1)
        self.assertEqual(self.user1.profile.followers_count, 1)
        self.assertEqual(self.user2.profile.following_count, 1)

        # Bob unfollows Alice
        res2 = self.client.post(reverse('toggle_follow', args=['alice']))
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertFalse(data2['is_following'])
        self.assertEqual(data2['followers_count'], 0)

        # Self-follow attempt via view
        self.client.login(username='alice', password='password123')
        self_follow_res = self.client.post(reverse('toggle_follow', args=['alice']))
        self.assertEqual(self_follow_res.status_code, 400)

        # Self-follow attempt via model
        with self.assertRaises(ValidationError):
            f = Follow(follower=self.user1, following=self.user1)
            f.save()

    def test_comment_system(self):
        """Test creating and deleting comments with author authorization."""
        post = Post.objects.create(user=self.user1, content="Discussion post")
        self.client.login(username='bob', password='password123')

        # Bob comments on Alice's post
        comment_res = self.client.post(
            reverse('add_comment', args=[post.id]),
            {'content': 'Great post Alice!'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(comment_res.status_code, 200)
        data = comment_res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['comments_count'], 1)
        comment_id = data['comment']['id']

        # Alice attempts to delete Bob's comment (forbidden)
        self.client.login(username='alice', password='password123')
        forbidden_del = self.client.post(
            reverse('delete_comment', args=[comment_id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(forbidden_del.status_code, 403)
        self.assertTrue(Comment.objects.filter(id=comment_id).exists())

        # Bob deletes his own comment (allowed)
        self.client.login(username='bob', password='password123')
        allowed_del = self.client.post(
            reverse('delete_comment', args=[comment_id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(allowed_del.status_code, 200)
        self.assertFalse(Comment.objects.filter(id=comment_id).exists())
