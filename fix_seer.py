import re

# Read the file
with open('werewolf_3panels.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all instances of "预言家?" with "预言家"
content = content.replace('预言家?', '预言家')
content = content.replace('预言家?', '预言家')  # Single quote version too

# Also fix other corrupted patterns
content = re.sub(r'预言家[?？]', '预言家', content)

# Write back
with open('werewolf_3panels.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("All occurrences of broken '预言家?' have been fixed to '预言家'")
