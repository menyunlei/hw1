#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Read the original file
with open('werewolf_3panels.py', 'rb') as f:
    raw_data = f.read()

# Decode with error handling
try:
    text = raw_data.decode('utf-8', errors='replace')
except Exception as e:
    print(f"Failed to decode: {e}")
    exit(1)

# Simple string replacements
replacements = [
    ('预言家)', '"预言家"'),  # Fix mismatched quote
    ('游戏)', '"游戏"'),  # Fix mismatched quote
]

for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        print(f"Replaced: {old} -> {new}")

# Remove any replacement characters (U+FFFD) that escaped into strings
text = text.replace('\ufffd', '')

# Write back
with open('werewolf_3panels.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("File cleaned and rewritten")
