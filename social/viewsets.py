# -*- coding: utf-8 -*-
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import Comment, Like, Post
from .notifications import notify_new_post, notify_new_comment
from .serializers import CommentSerializer, PostSerializer, PostCreateSerializer


class IsOwnerOrReadOnly(BasePermission):
    """Custom permission to only allow owners of an object to edit/delete it."""

    def has_object_permission(self, request, view, obj):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        return obj.author == request.user


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    filterset_fields = ["author"]
    ordering_fields = ["created_at"]
    ordering = "-created_at"
    permission_classes = [IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return PostCreateSerializer
        return PostSerializer

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        notify_new_post(post)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(
            post=post,
            user=request.user,
        )
        if not created:
            like.delete()
            return Response({"liked": False})
        return Response({"liked": True})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    ordering_fields = ["created_at"]
    ordering = "created_at"

    def perform_create(self, serializer):
        post_id = self.kwargs.get("post_pk")
        post = Post.objects.get(pk=post_id)
        comment = serializer.save(author=self.request.user, post=post)
        notify_new_comment(comment)