import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Pushes new notifications to a connected user: company-wide ones
    (e.g. low stock) and ones addressed personally to them."""

    async def connect(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated or not user.company_id:
            await self.close()
            return
        self.group_names = [
            f"company-{user.company_id}-notifications",
            f"user-{user.id}-notifications",
        ]
        for group_name in self.group_names:
            await self.channel_layer.group_add(group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        for group_name in getattr(self, "group_names", []):
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def notification_new(self, event):
        await self.send(text_data=json.dumps(event["data"]))
