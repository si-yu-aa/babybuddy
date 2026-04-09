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
    is_liked_by_me = serializers.SerializerMethodField()

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
            "created_at",
        ]
        read_only_fields = ["id", "author", "created_at"]

    def get_is_liked_by_me(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

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