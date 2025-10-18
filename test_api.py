import requests
import json

# API配置
api_base = "http://localhost:8080"
model = "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct"

# 测试消息
messages = [
    {"role": "system", "content": "你是一个狼人杀游戏的玩家。"},
    {"role": "user", "content": "请简单介绍一下你自己。"}
]

# 构造请求
payload = {
    "model": model,
    "messages": messages,
    "temperature": 0.7,
    "max_tokens": 200
}

print(f"Testing API: {api_base}/v1/chat/completions")
print(f"Model: {model}")
print(f"Request payload:")
print(json.dumps(payload, indent=2, ensure_ascii=False))
print("\n" + "="*60 + "\n")

try:
    # 发送请求
    response = requests.post(
        f"{api_base}/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30
    )

    print(f"Response Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("\n" + "="*60 + "\n")

    if response.status_code == 200:
        result = response.json()
        print("Response JSON:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 提取回复内容
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            print("\n" + "="*60 + "\n")
            print("Extracted Content:")
            print(content)

        # 显示token使用情况
        if "usage" in result:
            usage = result["usage"]
            print("\n" + "="*60 + "\n")
            print("Token Usage:")
            print(f"  Prompt tokens: {usage.get('prompt_tokens', 0)}")
            print(f"  Completion tokens: {usage.get('completion_tokens', 0)}")
            print(f"  Total tokens: {usage.get('total_tokens', 0)}")
    else:
        print(f"Error Response:")
        print(response.text)

except requests.exceptions.Timeout:
    print("ERROR: Request timed out after 30 seconds")
except requests.exceptions.ConnectionError as e:
    print(f"ERROR: Connection error: {e}")
except Exception as e:
    import traceback
    print(f"ERROR: {type(e).__name__}: {e}")
    print(f"Traceback:\n{traceback.format_exc()}")
