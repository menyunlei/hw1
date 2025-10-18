import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('werewolf_3panels.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix all backtick template literals to f-strings in Python sections (after line 1600)
fixed_count = 0
for i in range(1600, len(lines)):
    if '`' in lines[i]:
        # Convert `text ${var} text` to f"text {var} text"
        original = lines[i]
        # Replace backticks with quotes and ${} with {}
        lines[i] = lines[i].replace('`', '"')
        lines[i] = lines[i].replace('${', '{')

        # If line contains { }, make it an f-string
        if '{' in lines[i] and '}' in lines[i]:
            # Find the string literals and add f prefix
            lines[i] = re.sub(r'(\s+)(".*?")', r'\1f\2', lines[i])

        if lines[i] != original:
            fixed_count += 1
            print(f"Fixed line {i+1}")

with open('werewolf_3panels.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'\nTotal: Fixed {fixed_count} lines with backtick template literals')