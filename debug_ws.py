import re

with open('src/api/customer_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_endpoint = '''@app.websocket("/customer/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = Query(...), db: Session = Depends(get_db)):
    print(f"[WS] New connection attempt with session_id={session_id}")
    try:
        session = db.query(CustomerSession).filter(CustomerSession.session_id == session_id, CustomerSession.is_active == True).first()
        if not session:
            print(f"[WS] Session {session_id} not found or inactive. Rejecting.")
            await websocket.close(code=1008)
            return
        
        user_id = session.user_id
        print(f"[WS] Session {session_id} belongs to user_id={user_id}. Accepting...")
        await manager.connect(websocket, user_id)
        print(f"[WS] Connection accepted for user_id={user_id}.")
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            print(f"[WS] Client disconnected normally user_id={user_id}.")
            manager.disconnect(websocket, user_id)
        except Exception as e:
            print(f"[WS] Error in receive loop for user_id={user_id}: {e}")
            manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"[WS] Outer exception for session_id={session_id}: {e}")
'''

content = re.sub(
    r'@app\.websocket\("/customer/ws"\).*?(?=\nif __name__ == "__main__":|\Z)',
    new_endpoint + '\n',
    content,
    flags=re.DOTALL
)

with open('src/api/customer_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
