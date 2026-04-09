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