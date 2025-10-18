#!/usr/bin/env python3
"""
Fix JavaScript syntax mixed into Python code.
"""
import re

def fix_python_code():
    with open('werewolf_3panels.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Track if we're in HTML template
    in_html = False
    html_quote_count = 0
    fixed_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        orig_line = line

        # Track HTML sections (look for """ or ''')
        html_quote_count += line.count('"""') + line.count("'''")
        in_html = (html_quote_count % 2 == 1)

        # Only fix Python sections (not HTML/JavaScript)
        if not in_html and i > 15:  # Skip docstring at top
            stripped = line.strip()

            # Fix missing closing } for dicts
            if i > 0 and (stripped.startswith('"') or stripped.startswith("'")) and ':' in stripped:
                # Check if this looks like last line of dict but no closing }
                next_line = lines[i+1].strip() if i+1 < len(lines) else ""
                if next_line and not next_line.startswith('}') and not next_line.startswith(','):
                    # Check if previous lines suggest we're in a dict
                    prev_lines = ''.join(fixed_lines[-5:])
                    if '{' in prev_lines and prev_lines.count('{') > prev_lines.count('}'):
                        # Add closing }
                        indent = len(line) - len(line.lstrip())
                        line = line.rstrip() + '\n'
                        fixed_lines.append(line)
                        fixed_lines.append(' ' * (indent - 4) + '}\n')
                        i += 1
                        continue

        fixed_lines.append(line)
        i += 1

    with open('werewolf_3panels.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"Fixed {len(fixed_lines)} lines")

if __name__ == '__main__':
    fix_python_code()
