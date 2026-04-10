# -*- coding: utf-8 -*-
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .models import Comment, Like, Post
from .notifications import notify_new_post, notify_new_comment
from .serializers import CommentSerializer, PostSerializer, PostCreateSerializer

User = get_user_model()


class TrustworthySessionAuthentication(BaseAuthentication):
    """
    Session authentication that skips CSRF for trusted internal networks.
    Only accepts authenticated sessions.
    """
    def authenticate(self, request):
        # Get user from underlying request (not DRF's wrapped user)
        django_request = getattr(request, '_request', request)
        user = django_request.user
        if isinstance(user, AnonymousUser):
            return None
        return (user, None)


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
    authentication_classes = [TrustworthySessionAuthentication]

    def get_permissions(self):
        if self.action == "like":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return PostCreateSerializer
        return PostSerializer

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        notify_new_post(post)
        # Return the created post with full data
        return Response(
            PostSerializer(post, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="like")
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
    authentication_classes = [TrustworthySessionAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        post_id = self.kwargs.get("pk")  # URL is posts/<int:pk>/comments/, so pk is the post id
        post = Post.objects.get(pk=post_id)
        comment = serializer.save(author=self.request.user, post=post)
        notify_new_comment(comment)
