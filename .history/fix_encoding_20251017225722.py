import re
import sys

# Read the file with UTF-8 encoding and error handling
with open('werewolf_3panels.py', 'rb') as f:
    data = f.read()

# Decode with UTF-8, replacing broken sequences
try:
    text = data.decode('utf-8', errors='replace')
except Exception as e:
    print(f"Error decoding: {e}")
    sys.exit(1)

# Fix specific broken strings
text = text.replace('预言\ufffd', '预言家')  # \ufffd is the replacement character
text = text.replace('预言?', '预言家')  # Other broken variant

# Clean up any remaining issues - fix broken characters
text = re.sub(r'预言[^\w]', '预言家', text, flags=re.UNICODE)

# Write back with UTF-8 encoding
with open('werewolf_3panels.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("File fixed and rewritten with UTF-8 encoding")
