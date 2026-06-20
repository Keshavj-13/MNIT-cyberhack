import re

with open('App.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_marker = "  // Triggers key shuffle visual indicator\n"
end_marker = "  // --- Registration Handlers ---\n"

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if line == start_marker:
        start_idx = i
    if line == end_marker:
        end_idx = i

if start_idx != -1 and end_idx != -1:
    new_lines = lines[:start_idx] + lines[end_idx:]
    with open('App.tsx', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Deleted dead handlers from line", start_idx, "to", end_idx)
else:
    print("Markers not found", start_idx, end_idx)
