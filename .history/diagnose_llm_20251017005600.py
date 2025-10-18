#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM API 诊断工具
Diagnose LLM API connection and configuration issues
"""

import requests
import json
import sys
from pathlib import Path

def load_config():
    """加载 LLM 配置"""
    config_file = Path("llm_config.json")
    if not config_file.exists():
        print("❌ llm_config.json 文件不存在")
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print("✓ 配置文件加载成功:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return config
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return None

def test_api_connection(api_base, name):
    """测试 API 连接"""
    print(f"\n{'='*60}")
    print(f"测试 {name} API 连接")
    print(f"{'='*60}")
    print(f"📍 API Base: {api_base}")
    
    # 测试 /health 端点
    health_url = f"{api_base}/health"
    print(f"\n1️⃣  测试 /health 端点: {health_url}")
    try:
        response = requests.get(health_url, timeout=5)
        print(f"   ✓ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 连接失败 - API 服务未启动或地址错误")
        return False
    except requests.exceptions.Timeout:
        print(f"   ⏱️  请求超时")
        return False
    except Exception as e:
        print(f"   ⚠️  异常: {type(e).__name__}: {e}")
    
    # 测试 /v1/models 端点
    models_url = f"{api_base}/v1/models"
    print(f"\n2️⃣  测试 /v1/models 端点: {models_url}")
    try:
        response = requests.get(models_url, timeout=5)
        print(f"   ✓ Status: {response.status_code}")
        if response.status_code == 200:
            models_data = response.json()
            print(f"   Available Models:")
            if isinstance(models_data, dict) and "data" in models_data:
                for model in models_data.get("data", [])[:3]:
                    print(f"     - {model.get('id', 'Unknown')}")
            else:
                print(f"   {json.dumps(models_data, indent=2, ensure_ascii=False)[:300]}")
    except Exception as e:
        print(f"   ⚠️  异常: {type(e).__name__}: {e}")
    
    return True

def test_chat_api(api_base, model, name):
    """测试聊天 API"""
    print(f"\n3️⃣  测试 /v1/chat/completions (聊天) 端点")
    
    url = f"{api_base}/v1/chat/completions"
    print(f"   📍 URL: {url}")
    print(f"   📦 Model: {model}")
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hello, what is 1+1? Please respond with OUTPUT: [your answer] END"}
        ],
        "temperature": 0.1,
        "max_tokens": 100
    }
    
    print(f"\n   Sending test request...")
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"   ✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n   ✅ 聊天 API 成功!")
            
            # 提取响应内容
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                print(f"\n   Model Response:")
                print(f"   {content[:300]}")
                
                # 检查 OUTPUT 标记
                if "OUTPUT" in content or "output" in content:
                    print(f"\n   ✓ OUTPUT标记: ✅ 存在")
                else:
                    print(f"\n   ⚠️  OUTPUT标记: ❌ 不存在")
                
                if "END" in content or "end" in content:
                    print(f"   ✓ END标记: ✅ 存在")
                else:
                    print(f"   ⚠️  END标记: ❌ 不存在")
                
                # Token 统计
                usage = result.get("usage", {})
                print(f"\n   Token Usage:")
                print(f"     Prompt: {usage.get('prompt_tokens', 'N/A')}")
                print(f"     Completion: {usage.get('completion_tokens', 'N/A')}")
                print(f"     Total: {usage.get('total_tokens', 'N/A')}")
            else:
                print(f"\n   ⚠️  无法解析响应")
                print(f"   Full Response: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
        else:
            print(f"\n   ❌ API 返回错误: {response.status_code}")
            print(f"   Response: {response.text[:300]}")
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️  请求超时 (>30秒)")
        print(f"   💡 模型可能在加载或服务繁忙")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 连接失败 - API 服务未启动")
    except Exception as e:
        print(f"   ❌ 异常: {type(e).__name__}: {e}")

def main():
    print("🔍 LLM API 诊断工具")
    print("="*60)
    
    # 加载配置
    config = load_config()
    if not config:
        sys.exit(1)
    
    # 测试测试模型 API
    print("\n" + "="*60)
    print("第一部分: 测试模型 (Test Model)")
    print("="*60)
    
    test_api_base = config.get("test_api_base")
    test_model = config.get("test_model")
    
    if test_api_connection(test_api_base, "测试模型"):
        test_chat_api(test_api_base, test_model, "测试模型")
    
    # 测试NPC模型 API
    print("\n" + "="*60)
    print("第二部分: NPC模型")
    print("="*60)
    
    npc_api_base = config.get("npc_api_base")
    npc_model = config.get("npc_model")
    
    if test_api_connection(npc_api_base, "NPC模型"):
        test_chat_api(npc_api_base, npc_model, "NPC模型")
    
    # 诊断建议
    print("\n" + "="*60)
    print("🎯 诊断建议")
    print("="*60)
    
    print("""
如果看到 ❌ 连接失败，请检查:
  1. LLM 服务是否在运行?
     - vLLM: python -m vllm.entrypoints.openai.api_server --model <model_path>
     - Ollama: ollama serve
     - LM Studio: 检查 Local Server 是否启动
  
  2. API 地址是否正确?
     - 当前配置:
       - 测试模型: {test_api_base}
       - NPC模型: {npc_api_base}
     
     - 常见地址:
       - http://localhost:8000 (vLLM 默认)
       - http://localhost:11434 (Ollama 默认)
       - http://localhost:1234 (LM Studio 默认)
  
  3. 模型路径是否正确?
     - 当前配置:
       - 测试模型: {test_model}
       - NPC模型: {npc_model}
     
  4. 网络连接是否正常?
     - ping {test_api_base.split('://')[1].split(':')[0]} -n 4
""".format(
        test_api_base=test_api_base,
        npc_api_base=npc_api_base,
        test_model=test_model,
        npc_model=npc_model
    ))

if __name__ == "__main__":
    main()
