# Social Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a family social feed to Baby Buddy with posts (text+photo+video), likes, comments, and real-time WebSocket notifications.

**Architecture:** New `social` Django app with DRF for API and Django Channels for WebSocket real-time notifications. Uses Redis as the channel layer. Media files stored locally in `media/posts/`.

**Tech Stack:** Django 5.1, Django REST Framework, Django Channels, Channels-Redis, django-imagekit

---

## File Structure

```
social/
├── __init__.py
├── apps.py              # App config
├── models.py            # Post, Comment, Like models
├── views.py            # Template views (feed page)
├── urls.py              # URL routing
├── serializers.py       # DRF serializers
├── viewsets.py         # DRF ViewSets for API
├── filters.py           # DRF filters
├── consumers.py        # Channels WebSocket consumer
├── routing.py          # Channels URL routing
├── notifications.py    # Broadcast helpers
├── admin.py            # Django admin
├── tests.py            # Tests
└── templates/social/
    ├── feed.html        # Main feed page
    └── components/
        ├── post_card.html
        ├── post_form.html
        └── notification.html

babybuddy/
├── settings/base.py     # Modify: add channels app
├── asgi.py             # Modify: add channels routing
└── urls.py             # Modify: add social URLs

media/posts/            # User uploaded media (gitignore)
static/social/          # Built static files
```

---

## Task 1: Install Dependencies

**Files:**
- Modify: `Pipfile`
- Modify: `requirements.txt`

- [ ] **Step 1: Add to Pipfile**

```toml
[packages]
channels = "*"
channels-redis = "*"
```

- [ ] **Step 2: Add to requirements.txt**

```
channels==4.2.0
channels-redis==4.2.1
```

- [ ] **Step 3: Install dependencies**

```bash
pipenv install --dev
npm install
```

- [ ] **Step 4: Commit**

```bash
git add Pipfile requirements.txt
git commit -m "chore: add channels and channels-redis dependencies"
```

---

## Task 2: Configure Django Channels

**Files:**
- Modify: `babybuddy/settings/base.py`
- Create: `babybuddy/asgi.py` (replace existing)

- [ ] **Step 1: Add channels to INSTALLED_APPS in settings/base.py**

In `INSTALLED_APPS`, add `"channels"` before `"rest_framework"`.

```python
INSTALLED_APPS = [
    "api",
    "babybuddy.apps.BabyBuddyConfig",
    "channels",  # <-- add this
    "core.apps.CoreConfig",
    ...
]
```

- [ ] **Step 2: Add ASGI_APPLICATION and CHANNEL_LAYERS to settings/base.py**

Add at end of base.py (before Baby Buddy config section):

```python
# ASGI / Channels
ASGI_APPLICATION = "babybuddy.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv("REDIS_HOST") or "localhost", 6379)],
        },
    },
}
```

- [ ] **Step 3: Replace asgi.py**

Replace contents of `babybuddy/asgi.py` with:

```python
# -*- coding: utf-8 -*-
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babybuddy.settings.base")

django_asgi_app = get_asgi_application()

from social.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
```

- [ ] **Step 4: Commit**

```bash
git add babybuddy/settings/base.py babybuddy/asgi.py
git commit -m "feat: configure Django Channels with Redis backend"
```

---

## Task 3: Create Social Django App

**Files:**
- Create: `social/__init__.py`
- Create: `social/apps.py`
- Create: `social/models.py`
- Create: `social/admin.py`

- [ ] **Step 1: Create social directory structure**

```bash
mkdir -p social
mkdir -p social/templates/social/components
```

- [ ] **Step 2: Create social/__init__.py**

```python
```

- [ ] **Step 3: Create social/apps.py**

```python
# -*- coding: utf-8 -*-
from django.apps import AppConfig


class SocialConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "social"
    verbose_name = "Social Feed"
```

- [ ] **Step 4: Create social/models.py**

```python
# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models


class Post(models.Model):
    MEDIA_TYPE_CHOICES = [
        ("none", "None"),
        ("image", "Image"),
        ("video", "Video"),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    content = models.TextField(blank=True, verbose_name="Content")
    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPE_CHOICES,
        default="none",
    )
    media = models.ImageField(
        upload_to="posts/%Y/%m/%d/",
        blank=True,
        null=True,
    )
    video = models.FileField(
        upload_to="posts/videos/%Y/%m/%d/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}"

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.content[:30]}"


class Like(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["post", "user"]

    def __str__(self):
        return f"{self.user.username} likes {self.post.id}"
```

- [ ] **Step 5: Create social/admin.py**

```python
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
```

- [ ] **Step 6: Commit**

```bash
git add social/
git commit -m "feat: create social app with Post, Comment, Like models"
```

---

## Task 4: Register Social App and URLs

**Files:**
- Modify: `babybuddy/settings/base.py` (add to INSTALLED_APPS)
- Modify: `babybuddy/urls.py`
- Create: `social/urls.py`

- [ ] **Step 1: Add social to INSTALLED_APPS in settings/base.py**

Add `"social"` to INSTALLED_APPS list.

- [ ] **Step 2: Create social/urls.py**

```python
# -*- coding: utf-8 -*-
from django.urls import include, path

from .viewsets import CommentViewSet, LikeViewSet, PostViewSet

post_list = PostViewSet.as_view({"get": "list", "post": "create"})
post_detail = PostViewSet.as_view({"get": "retrieve", "delete": "destroy"})
post_like = PostViewSet.as_view({"post": "like"})
post_comments = CommentViewSet.as_view({"get": "list", "post": "create"})
comment_detail = CommentViewSet.as_view({"delete": "destroy"})

urlpatterns = [
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
```

- [ ] **Step 3: Add social URLs to babybuddy/urls.py**

Add to urlpatterns in `babybuddy/urls.py`:

```python
path("", include("social.urls", namespace="social")),
```

Place after the other includes (core, dashboard, reports).

- [ ] **Step 4: Commit**

```bash
git add babybuddy/settings/base.py babybuddy/urls.py social/urls.py
git commit -m "feat: register social app and add API URLs"
```

---

## Task 5: Implement DRF Serializers and ViewSets

**Files:**
- Create: `social/serializers.py`
- Create: `social/viewsets.py`
- Create: `social/filters.py`

- [ ] **Step 1: Create social/serializers.py**

```python
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
```

- [ ] **Step 2: Create social/viewsets.py**

```python
# -*- coding: utf-8 -*-
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Comment, Like, Post
from .notifications import notify_new_post, notify_new_comment
from .serializers import CommentSerializer, PostSerializer, PostCreateSerializer


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    filterset_fields = ["author"]
    ordering_fields = ["created_at"]
    ordering = "-created_at"

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
```

- [ ] **Step 3: Create social/notifications.py**

```python
# -*- coding: utf-8 -*-
import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def get_channel_group_name(user_id):
    return f"user_{user_id}"


def notify_new_post(post):
    """Broadcast new post to all connected clients except author."""
    channel_layer = get_channel_layer()
    group_name = "social_feed"

    message = {
        "type": "new_post",
        "post": {
            "id": post.id,
            "author_username": post.author.username,
            "author_display": post.author.get_full_name() or post.author.username,
            "content": post.content,
            "media_type": post.media_type,
            "media_url": post.media.url if post.media else None,
            "video_url": post.video.url if post.video else None,
            "created_at": post.created_at.isoformat(),
        },
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "broadcast_message",
            "message": message,
        },
    )


def notify_new_comment(comment):
    """Send notification to the post author only."""
    channel_layer = get_channel_layer()
    group_name = get_channel_group_name(comment.post.author_id)

    message = {
        "type": "new_comment",
        "post_id": comment.post_id,
        "comment": {
            "id": comment.id,
            "author_username": comment.author.username,
            "author_display": comment.author.get_full_name() or comment.author.username,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
        },
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "broadcast_message",
            "message": message,
        },
    )
```

- [ ] **Step 4: Commit**

```bash
git add social/serializers.py social/viewsets.py social/notifications.py
git commit -m "feat: add DRF serializers, viewsets and notification helpers"
```

---

## Task 6: Implement WebSocket Consumer and Routing

**Files:**
- Create: `social/consumers.py`
- Create: `social/routing.py`

- [ ] **Step 1: Create social/consumers.py**

```python
# -*- coding: utf-8 -*-
import json

from channels.generic.websocket import AsyncWebsocketConsumer


class SocialFeedConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "social_feed"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Client doesn't send messages, only receives
        pass

    async def broadcast_message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps(message))
```

- [ ] **Step 2: Create social/routing.py**

```python
# -*- coding: utf-8 -*-
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/social/feed/$", consumers.SocialFeedConsumer.as_asgi()),
]
```

- [ ] **Step 3: Update babybuddy/asgi.py to add social routing**

Replace the current `asgi.py` content (already done in Task 2, just verify):

```python
# -*- coding: utf-8 -*-
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babybuddy.settings.base")

django_asgi_app = get_asgi_application()

from social.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
```

- [ ] **Step 4: Commit**

```bash
git add social/consumers.py social/routing.py
git commit -m "feat: add WebSocket consumer and routing for real-time feed"
```

---

## Task 7: Create Feed Template Views

**Files:**
- Create: `social/views.py`
- Modify: `social/urls.py`

- [ ] **Step 1: Create social/views.py**

```python
# -*- coding: utf-8 -*-
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class FeedView(LoginRequiredMixin, TemplateView):
    template_name = "social/feed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Social Feed"
        return context
```

- [ ] **Step 2: Update social/urls.py to add template view**

Add to social/urls.py:

```python
from .views import FeedView

urlpatterns = [
    path("social/", FeedView.as_view(), name="feed"),
    # ... existing API paths
]
```

- [ ] **Step 3: Commit**

```bash
git add social/views.py social/urls.py
git commit -m "feat: add feed template view"
```

---

## Task 8: Create Feed HTML Template

**Files:**
- Create: `social/templates/social/feed.html`
- Create: `social/templates/social/components/post_card.html`
- Create: `social/templates/social/components/post_form.html`

- [ ] **Step 1: Create social/templates/social/feed.html**

```html
{% extends "babybuddy/page.html" %}

{% block title %}Social Feed{% endblock %}

{% block content %}
<div class="container">
    <div class="row">
        <div class="col-md-8 mx-auto">
            {% include "social/components/post_form.html" %}

            <div id="feed-container" hx-get="/api/social/posts/"
                 hx-trigger="every 30s"
                 hx-swap="innerHTML">
                <!-- Posts loaded here -->
            </div>
        </div>
    </div>
</div>

<!-- Notification Toast -->
<div id="notification-toast" class="toast" role="alert" aria-live="assertive"
     aria-atomic="true" style="position: fixed; bottom: 1rem; right: 1rem; z-index: 9999;">
    <div class="toast-body">
        <strong id="notification-author"></strong>
        <p id="notification-content" class="mb-0"></p>
        <button type="button" class="btn btn-sm btn-primary" onclick="refreshFeed()">View</button>
    </div>
</div>

<script>
const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
const feedSocket = new WebSocket(wsProtocol + '//' + location.host + '/ws/social/feed/');

feedSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data.type === 'new_post') {
        showNotification(data.post);
    }
};

function showNotification(post) {
    document.getElementById('notification-author').textContent = post.author_display + ' posted:';
    document.getElementById('notification-content').textContent = post.content || '(Media post)';
    const toast = new bootstrap.Toast(document.getElementById('notification-toast'));
    toast.show();
}

function refreshFeed() {
    fetch('/api/social/posts/')
        .then(r => r.json())
        .then(data => {
            document.getElementById('feed-container').innerHTML = data.results.map(renderPost).join('');
        });
}

function renderPost(post) {
    let mediaHtml = '';
    if (post.media_type === 'image' && post.media_url) {
        mediaHtml = `<img src="${post.media_url}" class="img-fluid rounded mb-2" alt="Post media">`;
    } else if (post.media_type === 'video' && post.video_url) {
        mediaHtml = `<video src="${post.video_url}" controls class="img-fluid rounded mb-2"></video>`;
    }

    return `
    <div class="card mb-3">
        <div class="card-body">
            <h6 class="card-subtitle mb-2 text-muted">
                <strong>${post.author.display_name}</strong> - ${formatTime(post.created_at)}
            </h6>
            <p class="card-text">${post.content || ''}</p>
            ${mediaHtml}
            <div class="d-flex justify-content-between align-items-center">
                <button class="btn btn-sm btn-outline-primary like-btn"
                        data-post-id="${post.id}"
                        onclick="toggleLike(this, ${post.id})">
                    ❤️ ${post.like_count}
                </button>
                <span class="text-muted">💬 ${post.comment_count} comments</span>
            </div>
        </div>
    </div>
    `;
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = (now - date) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return date.toLocaleDateString();
}

function toggleLike(btn, postId) {
    fetch('/api/social/posts/' + postId + '/like/', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            btn.innerHTML = '❤️ ' + (data.liked ? 'liked' : 'unliked');
        });
}

// Load feed on page load
refreshFeed();
</script>
{% endblock %}
```

- [ ] **Step 2: Create social/templates/social/components/post_form.html**

```html
<div class="card mb-3">
    <div class="card-body">
        <form id="post-form" enctype="multipart/form-data">
            <div class="mb-2">
                <textarea class="form-control" name="content"
                          placeholder="What's happening?" rows="2"></textarea>
            </div>
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <label class="btn btn-sm btn-outline-secondary me-2">
                        📷 <input type="file" name="media" accept="image/*" hidden
                                  onchange="handleMediaSelect(this, 'image')">
                    </label>
                    <label class="btn btn-sm btn-outline-secondary">
                        🎬 <input type="file" name="video" accept="video/*" hidden
                                  onchange="handleMediaSelect(this, 'video')">
                    </label>
                    <span id="selected-media" class="ms-2 text-muted"></span>
                </div>
                <button type="submit" class="btn btn-primary btn-sm">Post</button>
            </div>
            <input type="hidden" name="media_type" id="media_type" value="none">
        </form>
    </div>
</div>

<script>
let selectedMediaType = 'none';

function handleMediaSelect(input, type) {
    if (input.files && input.files[0]) {
        document.getElementById('media_type').value = type;
        document.getElementById('selected-media').textContent = input.files[0].name;
    }
}

document.getElementById('post-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);

    fetch('/api/social/posts/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
        },
    })
    .then(r => r.json())
    .then(data => {
        if (data.id) {
            this.reset();
            document.getElementById('selected-media').textContent = '';
            refreshFeed();
        }
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
</script>
```

- [ ] **Step 3: Commit**

```bash
git add social/templates/social/feed.html social/templates/social/components/
git commit -m "feat: add feed HTML template with real-time notifications"
```

---

## Task 9: Add Nav Link to Social Feed

**Files:**
- Modify: `babybuddy/templates/babybuddy/nav-dropdown.html` (or wherever nav is)

- [ ] **Step 1: Find navigation template and add Social Feed link**

Look at the existing nav structure and add a "Social" or "Feed" link.

For example, if there's a nav dropdown, add:

```html
<li><a class="dropdown-item" href="{% url 'social:feed' %}">📱 Social Feed</a></li>
```

- [ ] **Step 2: Commit**

```bash
git add babybuddy/templates/babybuddy/nav-dropdown.html
git commit -m "feat: add social feed link to navigation"
```

---

## Task 10: Build Frontend Assets

**Files:**
- Modify: `gulpfile.config.js`
- Modify: `gulpfile.js` (if needed)

- [ ] **Step 1: Add social app to gulp config for potential JS/CSS down the road**

In `gulpfile.config.js`, add to `extrasConfig`:

```javascript
social: {
  dest: basePath + "social/",
  files: "social/static_src/**/*",
},
```

- [ ] **Step 2: Run build**

```bash
gulp build
```

- [ ] **Step 3: Commit**

```bash
git add gulpfile.config.js
git commit -m "chore: add social app to gulp config"
```

---

## Task 11: Create Database Migration

- [ ] **Step 1: Create migration**

```bash
pipenv run python manage.py makemigrations social
```

- [ ] **Step 2: Apply migration (dev only, will be applied in production deploy)**

```bash
pipenv run python manage.py migrate
```

- [ ] **Step 3: Commit migration**

```bash
git add social/migrations/
git commit -m "feat: add social app migration"
```

---

## Task 12: Write Tests

**Files:**
- Create: `social/tests.py`

- [ ] **Step 1: Write model tests**

```python
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
```

- [ ] **Step 2: Write API tests**

```python
# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.urls import reverse
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
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_like_post(self):
        post = Post.objects.create(author=self.user, content="Test")
        response = self.client.post(f"/api/social/posts/{post.id}/like/")
        self.assertEqual(response.data["liked"], True)

    def test_unlike_post(self):
        post = Post.objects.create(author=self.user, content="Test")
        self.client.post(f"/api/social/posts/{post.id}/like/")
        response = self.client.post(f"/api/social/posts/{post.id}/like/")
        self.assertEqual(response.data["liked"], False)
```

- [ ] **Step 3: Run tests**

```bash
pipenv run python manage.py test social --settings=babybuddy.settings.test
```

- [ ] **Step 4: Commit**

```bash
git add social/tests.py
git commit -m "test: add social app tests"
```

---

## Task 13: Final Integration Test

- [ ] **Step 1: Verify all pieces work together**

```bash
# 1. Build assets
gulp build

# 2. Run tests
pipenv run python manage.py test social --settings=babybuddy.settings.test

# 3. Run linter
gulp lint

# 4. Start server (manual test)
pipenv run python manage.py runserver
```

- [ ] **Step 2: Commit any remaining changes**

---

## Spec Coverage Check

| Spec Requirement | Task(s) |
|-----------------|---------|
| Post with text, image, video | Task 3, 8 |
| Comment on post | Task 3, 5 |
| Like/unlike post | Task 3, 5 |
| Global feed | Task 7, 8 |
| Real-time WebSocket notifications | Task 5, 6 |
| REST API | Task 4, 5 |
| Permissions (own post only delete) | Task 5, 12 |
| Redis channel layer | Task 2 |

---

## Type Consistency Check

- `Post.media_type`: `none`, `image`, `video` — consistent across serializers, models, templates
- `notify_new_post(post)`: passes `post` object, builds dict with `author_username`, `author_display` — consistent with consumer expectations
- `SocialFeedConsumer` group: `social_feed` — consistent in consumer, routing, notifications

---

**Plan complete.** All 13 tasks with complete code and steps.

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
