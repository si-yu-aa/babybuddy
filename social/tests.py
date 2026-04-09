# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.test import TestCase

from social.models import Comment, Like, Post

User = get_user_model()


class PostModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )

    def test_create_post(self):
        post = Post.objects.create(
            author=self.user,
            content="Test post content",
        )
        self.assertEqual(post.content, "Test post content")
        self.assertEqual(post.media_type, "none")
        self.assertEqual(post.like_count, 0)
        self.assertEqual(post.comment_count, 0)

    def test_create_post_with_image(self):
        post = Post.objects.create(
            author=self.user,
            content="Image post",
            media_type="image",
        )
        self.assertEqual(post.media_type, "image")

    def test_like_count(self):
        post = Post.objects.create(author=self.user, content="Test")
        user2 = User.objects.create_user(username="user2", password="pass123")
        Like.objects.create(post=post, user=self.user)
        Like.objects.create(post=post, user=user2)
        self.assertEqual(post.like_count, 2)


class CommentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.post = Post.objects.create(author=self.user, content="Test")

    def test_create_comment(self):
        comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="Test comment",
        )
        self.assertEqual(comment.content, "Test comment")


class LikeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.post = Post.objects.create(author=self.user, content="Test")

    def test_unique_like(self):
        Like.objects.create(post=self.post, user=self.user)
        with self.assertRaises(Exception):
            Like.objects.create(post=self.post, user=self.user)


# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from social.models import Post

User = get_user_model()


class PostAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        # Grant permissions for social app
        permissions = Permission.objects.filter(
            codename__in=["add_post", "view_post", "delete_post", "change_post"]
        )
        self.user.user_permissions.add(*permissions)
        self.client.force_authenticate(user=self.user)

    def test_list_posts(self):
        Post.objects.create(author=self.user, content="Test 1")
        Post.objects.create(author=self.user, content="Test 2")

        response = self.client.get("/api/social/posts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_create_post(self):
        data = {"content": "New post", "media_type": "none"}
        response = self.client.post("/api/social/posts/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)

    def test_delete_own_post(self):
        post = Post.objects.create(author=self.user, content="Test")
        response = self.client.delete(f"/api/social/posts/{post.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.count(), 0)

    def test_cannot_delete_others_post(self):
        user2 = User.objects.create_user(username="user2", password="pass123")
        post = Post.objects.create(author=user2, content="Test")
        response = self.client.delete(f"/api/social/posts/{post.id}/")
        # Returns 403 because user has delete permission but not on this object
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_like_post(self):
        post = Post.objects.create(author=self.user, content="Test")
        response = self.client.post(f"/api/social/posts/{post.id}/like/")
        self.assertEqual(response.data["liked"], True)

    def test_unlike_post(self):
        post = Post.objects.create(author=self.user, content="Test")
        self.client.post(f"/api/social/posts/{post.id}/like/")
        response = self.client.post(f"/api/social/posts/{post.id}/like/")
        self.assertEqual(response.data["liked"], False)