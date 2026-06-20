import re

with open('App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Delete unused handlers
handlers_start = "  const animateKeyRotation = "
handlers_end = "  const handleRegSubmit = "

start_idx = content.find(handlers_start)
end_idx = content.find(handlers_end)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + content[end_idx:]
    with open('App.tsx', 'w', encoding='utf-8') as f:
        f.write(new_content)
