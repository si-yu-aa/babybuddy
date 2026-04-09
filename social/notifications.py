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