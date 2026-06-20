import re

with open('src/api/customer_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The block to move
block_start = "# WebSocket Connection Manager"
block_end = "manager.disconnect(websocket, user_id)\n"

start_idx = content.find(block_start)
end_idx = content.find(block_end) + len(block_end)

if start_idx != -1 and end_idx != -1:
    ws_block = content[start_idx:end_idx]
    
    # Remove from current position
    content = content[:start_idx] + content[end_idx:]
    
    # Insert at the end of the file, just before `if __name__ == "__main__":`
    main_idx = content.find('if __name__ == "__main__":')
    if main_idx != -1:
        content = content[:main_idx] + ws_block + '\n' + content[main_idx:]
    
    with open('src/api/customer_api.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Moved WebSocket block successfully.")
else:
    print("Could not find WebSocket block.")
