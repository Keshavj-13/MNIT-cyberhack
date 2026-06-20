import re

with open('src/api/customer_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
if 'WebSocket' not in content:
    content = content.replace(
        'from fastapi import FastAPI, Depends, HTTPException, Body, Security, Response, Cookie',
        'from fastapi import FastAPI, Depends, HTTPException, Body, Security, Response, Cookie, WebSocket, WebSocketDisconnect, Query'
    )

# Add ConnectionManager class and instance after CORS setup
manager_code = """
# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        # Maps user_id (int) to list of WebSockets
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

@app.websocket("/customer/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = Query(...), db: Session = Depends(get_db)):
    session = db.query(CustomerSession).filter(CustomerSession.session_id == session_id, CustomerSession.is_active == True).first()
    if not session:
        await websocket.close(code=1008)
        return
    
    user_id = session.user_id
    await manager.connect(websocket, user_id)
    try:
        while True:
            # We don't expect messages from client, but we must receive to keep connection open and detect disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
"""

if 'class ConnectionManager:' not in content:
    # insert before `# DB Dependency`
    content = content.replace('# DB Dependency', manager_code + '\n# DB Dependency')

with open('src/api/customer_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
