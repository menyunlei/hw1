import requests
import re

# Get the page
response = requests.get('http://localhost:5005')
content = response.text

# Find the script section
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    script = script_match.group(1)

    print("JavaScript Analysis:")
    print("=" * 50)

    # Check for basic syntax balance
    print(f"Open parentheses: {script.count('(')}")
    print(f"Close parentheses: {script.count(')')}")
    print(f"Open braces: {script.count('{')}")
    print(f"Close braces: {script.count('}')}")
    print(f"Open brackets: {script.count('[')}")
    print(f"Close brackets: {script.count(']')}")

    # Check for template literals
    backticks = script.count('`')
    print(f"\nBackticks found: {backticks}")

    # Look for common JS errors
    if 'for (' not in script and 'for(' not in script:
        print("\nWarning: No for loops found")

    # Check if main functions are defined
    functions = ['startGame', 'stopGame', 'showEvaluation', 'toggleAutoMode']
    print("\nFunction definitions found:")
    for func in functions:
        if f'function {func}' in script:
            print(f"  + {func}")
        else:
            print(f"  - {func}")

    # Look for syntax error patterns
    print("\nPotential issues:")
    if '};' in script:
        positions = [i for i, c in enumerate(script) if script[i:i+2] == '};']
        print(f"  - Found }}; at positions: {positions[:5]}...")

    # Save script for manual inspection
    with open('extracted_script.js', 'w', encoding='utf-8') as f:
        f.write(script)
    print("\nScript saved to extracted_script.js for inspection")
else:
    print("No script tag found!")