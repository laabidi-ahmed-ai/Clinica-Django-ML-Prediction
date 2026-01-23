from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from .models import ChatRoom, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        sender = self.scope['user']

        # Simple protocol: {type: 'message', message: '...', client_id: 'c-...'}
        msg_type = data.get('type') or 'message'

        if msg_type == 'message':
            message_text = data.get('message')
            client_id = data.get('client_id')

            # Save message to DB and get full object
            msg_obj = await database_sync_to_async(Message.objects.create)(
                room_id=self.room_id,
                sender=sender,
                content=message_text
            )

            # Broadcast saved message with id and timestamp (ISO)
            await self.channel_layer.group_send(
                f'chat_{self.room_id}',
                {
                    'type': 'chat_message',
                    'message': msg_obj.content,
                    'sender': {
                        'username': sender.username,
                        'first_name': getattr(sender, 'first_name', ''),
                        'last_name': getattr(sender, 'last_name', '')
                    },
                    'id': msg_obj.id,
                    'time': msg_obj.timestamp.strftime('%H:%M'),
                    'client_id': client_id,
                }
            )

        # future handlers (voice, like) can be added here

    async def chat_message(self, event):
        # Send message to WebSocket
        payload = {
            'message': event.get('message'),
            'sender': event.get('sender'),
            'id': event.get('id'),
            'time': event.get('time'),
            'client_id': event.get('client_id')
        }
        await self.send(text_data=json.dumps(payload))
