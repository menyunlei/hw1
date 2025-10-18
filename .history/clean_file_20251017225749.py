#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

# Read the original file
with open('werewolf_3panels.py', 'rb') as f:
    raw_data = f.read()

# Decode with error handling
try:
    text = raw_data.decode('utf-8', errors='ignore')
except Exception as e:
    print(f"Failed to decode: {e}")
    exit(1)

# Fix broken strings and other issues
fixes = [
    (r'预言家)', '预言家'),  # Fix missing opening quote
    (r'预言家[\ufffd]', '预言家'),  # Replacement char
    (r'游戏[\ufffd]', '游戏'),  # Replacement char
    (r'分析[\ufffd]', '分析'),  # Replacement char
    (r'配置[\ufffd]', '配置'),  # Replacement char
    (r'模式[\ufffd]', '模式'),  # Replacement char
    (r'[\ufffd]""', '""'),  # Ending replacement char
    (r'[\ufffd]["""\']', '"'),  # Broken quotes
]

for pattern, replacement in fixes:
    text = re.sub(pattern, replacement, text)

# Write back
with open('werewolf_3panels.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("File cleaned and rewritten")
