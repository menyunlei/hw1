import requests
import sys
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    response = requests.get('http://localhost:5005')

    if response.status_code == 200:
        html_content = response.text

        # Check if eval button exists
        if 'btn-eval' in html_content:
            print("✅ 评估按钮存在于HTML中!")

            # Find button position
            button_index = html_content.find('btn-eval')
            snippet = html_content[max(0, button_index-100):button_index+200]
            print("\n按钮HTML片段:")
            print(snippet)
        else:
            print("❌ 评估按钮不在HTML中!")

        # Check for showEvaluation function
        if 'showEvaluation' in html_content:
            print("\n✅ showEvaluation函数存在!")
        else:
            print("\n❌ showEvaluation函数不存在!")

        # Count all buttons
        button_count = html_content.count('<button')
        print(f"\n总按钮数: {button_count}")

        # List all button IDs
        import re
        button_ids = re.findall(r'id="(btn-[^"]+)"', html_content)
        print(f"\n所有按钮ID: {button_ids}")

    else:
        print(f"❌ 服务器响应错误: {response.status_code}")

except Exception as e:
    print(f"❌ 连接错误: {e}")
    print("\n请确保服务器在 http://localhost:5005 运行")