import re

with open('src/api/customer_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'BackgroundTasks' not in content:
    content = content.replace(
        'from fastapi import FastAPI, Depends, HTTPException, Body, Security, Response, Cookie, WebSocket, WebSocketDisconnect, Query',
        'from fastapi import FastAPI, Depends, HTTPException, Body, Security, Response, Cookie, WebSocket, WebSocketDisconnect, Query, BackgroundTasks'
    )

old_def = 'def confirm_transfer(payload: EncryptedPayload = Body(...), user_payload = Depends(get_current_user_payload), db: Session = Depends(get_db)):'
new_def = 'def confirm_transfer(payload: EncryptedPayload = Body(...), user_payload = Depends(get_current_user_payload), db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):'

content = content.replace(old_def, new_def)

# Add broadcast after db.commit() at line 809
old_commit = """    db.add(sender_ledger)
    db.add(receiver_ledger)
    db.commit()"""

new_commit = """    db.add(sender_ledger)
    db.add(receiver_ledger)
    db.commit()
    
    if background_tasks:
        background_tasks.add_task(
            manager.send_personal_message,
            {
                "type": "INCOMING_TRANSFER",
                "amount": tx.amount,
                "sender": sender.username,
                "timestamp": datetime.datetime.utcnow().isoformat()
            },
            receiver.id
        )"""

content = content.replace(old_commit, new_commit)

with open('src/api/customer_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
