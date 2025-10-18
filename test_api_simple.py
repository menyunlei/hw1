import requests
import json

# API配置
api_base = "http://localhost:8080"
model = "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct"

# 简单测试消息
messages = [
    {"role": "user", "content": "Say hello in one sentence."}
]

# 构造请求
payload = {
    "model": model,
    "messages": messages,
    "temperature": 0.7,
    "max_tokens": 50
}

print(f"Testing API: {api_base}/v1/chat/completions")
print(f"Model: {model}")
print(f"Sending simple test...")
print("\n" + "="*60 + "\n")

try:
    # 发送请求（增加超时时间）
    response = requests.post(
        f"{api_base}/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=120  # 2分钟超时
    )

    print(f"Response Status Code: {response.status_code}")
    print("\n" + "="*60 + "\n")

    if response.status_code == 200:
        result = response.json()
        print("Success! API is working.")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 提取回复内容
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            print("\n" + "="*60 + "\n")
            print("LLM Response:")
            print(content)
    else:
        print(f"Error Response ({response.status_code}):")
        print(response.text)

except requests.exceptions.Timeout:
    print("ERROR: Request timed out after 120 seconds")
    print("The API server might be slow or overloaded.")
except requests.exceptions.ConnectionError as e:
    print(f"ERROR: Cannot connect to API server: {e}")
    print("Make sure the server is running at http://localhost:8080")
except Exception as e:
    import traceback
    print(f"ERROR: {type(e).__name__}: {e}")
    print(f"Traceback:\n{traceback.format_exc()}")
