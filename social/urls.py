# -*- coding: utf-8 -*-
from django.urls import path

from .views import FeedView
from .viewsets import CommentViewSet, PostViewSet

post_list = PostViewSet.as_view({"get": "list", "post": "create"})
post_detail = PostViewSet.as_view({"get": "retrieve", "delete": "destroy"})
post_like = PostViewSet.as_view({"post": "like"})
post_comments = CommentViewSet.as_view({"get": "list", "post": "create"})
comment_detail = CommentViewSet.as_view({"delete": "destroy"})

urlpatterns = [
    path("social/", FeedView.as_view(), name="feed"),
    path("api/social/posts/", post_list, name="post-list"),
    path("api/social/posts/<int:pk>/", post_detail, name="post-detail"),
    path("api/social/posts/<int:pk>/like/", post_like, name="post-like"),
    path(
        "api/social/posts/<int:pk>/comments/",
        post_comments,
        name="post-comments",
    ),
    path(
        "api/social/comments/<int:pk>/",
        comment_detail,
        name="comment-detail",
    ),
]