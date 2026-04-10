# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Comment, Like, Post

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "display_name"]

    def get_display_name(self, obj):
        return obj.get_full_name() or obj.username


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    media_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    is_liked_by_me = serializers.SerializerMethodField()
    liked_by = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "content",
            "media_type",
            "media_url",
            "video_url",
            "like_count",
            "comment_count",
            "is_liked_by_me",
            "liked_by",
            "comments",
            "created_at",
        ]
        read_only_fields = ["id", "author", "created_at"]

    def get_is_liked_by_me(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_liked_by(self, obj):
        likes = obj.likes.all().select_related('user')[:10]  # Limit to 10 most recent
        return [{'id': like.user.id, 'username': like.user.username, 'display_name': like.user.get_full_name() or like.user.username} for like in likes]

    def get_comments(self, obj):
        comments = obj.comments.all().select_related('author')[:20]
        return [{'id': c.id, 'author': {'id': c.author.id, 'username': c.author.username, 'display_name': c.author.get_full_name() or c.author.username}, 'content': c.content, 'created_at': c.created_at.isoformat()} for c in comments]

    def get_media_url(self, obj):
        if obj.media:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.media.url)
        return None

    def get_video_url(self, obj):
        if obj.video:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.video.url)
        return None


class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["content", "media_type", "media", "video"]


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at"]
        read_only_fields = ["id", "author", "created_at"]