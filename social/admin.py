# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Comment, Like, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["author", "content", "media_type", "created_at"]
    list_filter = ["media_type", "created_at"]
    search_fields = ["content", "author__username"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["author", "post", "content", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["content", "author__username"]


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ["user", "post", "created_at"]