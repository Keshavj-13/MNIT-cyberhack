import re

with open('src/api/customer_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the argument type hints in ConnectionManager just to be clean
content = content.replace(
    'async def connect(self, websocket: WebSocket, user_id: int):',
    'async def connect(self, websocket: WebSocket, user_id: str):'
)
content = content.replace(
    'def disconnect(self, websocket: WebSocket, user_id: int):',
    'def disconnect(self, websocket: WebSocket, user_id: str):'
)
content = content.replace(
    'async def send_personal_message(self, message: dict, user_id: int):',
    'async def send_personal_message(self, message: dict, user_id: str):'
)

# Fix the broadcast in confirm_transfer to use receiver.username instead of receiver.id
old_broadcast = """        background_tasks.add_task(
            manager.send_personal_message,
            {
                "type": "INCOMING_TRANSFER",
                "amount": tx.amount,
                "sender": sender.username,
                "timestamp": datetime.datetime.utcnow().isoformat()
            },
            receiver.id
        )"""

new_broadcast = """        background_tasks.add_task(
            manager.send_personal_message,
            {
                "type": "INCOMING_TRANSFER",
                "amount": tx.amount,
                "sender": sender.username,
                "timestamp": datetime.datetime.utcnow().isoformat()
            },
            receiver.username
        )"""

content = content.replace(old_broadcast, new_broadcast)

with open('src/api/customer_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
