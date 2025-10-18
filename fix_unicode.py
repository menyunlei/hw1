"""
Fix Unicode issues in Python files for Windows compatibility
"""

import re
import os

def clean_unicode_in_file(filepath):
    """Remove or replace Unicode characters in print statements"""

    # Map of Unicode to ASCII replacements
    replacements = {
        '🐺': '[WOLF]',
        '👑': '[KING]',
        '🔮': '[SEER]',
        '🧙': '[WITCH]',
        '🎯': '[HUNTER]',
        '🛡️': '[GUARD]',
        '👨‍🌾': '[VILLAGER]',
        '🧑‍⚖️': '[JUDGE]',
        '✅': '[OK]',
        '⚠️': '[WARN]',
        '❌': '[ERROR]',
        '🔍': '[TEST]',
        '🌐': '[WEB]',
        '📺': '[VIEW]',
        '🎮': '[GAME]',
        '📊': '[STATS]',
        '🏆': '[WIN]',
        '⏱️': '[TIME]',
        '👮': '[SHERIFF]',
        '⚖️': '[BALANCE]',
        '⏰': '[CLOCK]',
        '📈': '[CHART]',
        '💾': '[SAVE]',
        '💡': '[TIP]',
        '📡': '[API]',
        '🤖': '[BOT]',
        '🌡️': '[TEMP]',
        '📝': '[TEXT]',
        '👥': '[PEOPLE]',
        '📋': '[LIST]',
        '🌙': '[NIGHT]',
        '☀️': '[DAY]',
        '🗳️': '[VOTE]',
        '💬': '[TALK]',
        '🎲': '[DICE]',
        '🔄': '[CYCLE]',
        '📌': '[PIN]',
        '🚨': '[ALERT]',
        '🏷️': '[TAG]',
        '📖': '[BOOK]',
        '🌟': '[STAR]',
        '🎭': '[MASK]',
        '🕵️': '[DETECT]',
        '🏃': '[RUN]',
        '🛑': '[STOP]',
        '👁️': '[EYE]',
        '🌀': '[SPIN]',
        '⚔️': '[BATTLE]',
        '🎯': '[TARGET]',
        '🔥': '[FIRE]',
        '💭': '[THINK]',
        '🎮': '',
        '🌐': '',
        '🧑‍⚖': '',
        '👨‍🌾': '',
        '🛡': '',
        '🧙‍♀': '',
        '🚨': '',
        '📌': ''
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Count replacements
        count = 0

        # Replace Unicode characters
        for unicode_char, ascii_replacement in replacements.items():
            if unicode_char in content:
                content = content.replace(unicode_char, ascii_replacement)
                count += content.count(unicode_char)

        # Remove any remaining non-ASCII characters in print statements
        lines = content.split('\n')
        new_lines = []

        for line in lines:
            if 'print' in line:
                # Replace any remaining Unicode characters with their escape codes
                new_line = ''
                for char in line:
                    if ord(char) > 127:
                        new_line += ''  # Remove non-ASCII
                    else:
                        new_line += char
                new_lines.append(new_line)
            else:
                new_lines.append(line)

        content = '\n'.join(new_lines)

        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return count

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return 0

# Fix main files
files_to_fix = [
    'werewolf_game.py',
    'realtime_observer.py',
    'run_game.py',
    'run_with_observer.py'
]

print("Fixing Unicode issues in Python files...")
print("="*50)

for filename in files_to_fix:
    if os.path.exists(filename):
        count = clean_unicode_in_file(filename)
        print(f"Fixed {filename}")

print("="*50)
print("Unicode cleanup complete!")
print("\nYou can now run the game without encoding errors.")