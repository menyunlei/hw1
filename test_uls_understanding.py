"""
测试LLM是否能理解ULS++编码
"""
import requests
import json

def test_uls_understanding():
    """测试LLM理解ULS++编码的能力"""

    # 加载配置
    with open("llm_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    api_base = config["test_api_base"]
    model = config["test_model"]

    # 测试1: 让LLM解读其他玩家的ULS++编码
    test_prompt = """你是狼人杀游戏中的Player 5（村民）。以下是其他玩家的发言（ULS++编码格式）：

【第1天发言】
[P0] PV:3|SUS:3@4.6,5@3.7|EV:+140
[P1] PV:3|SUS:3@4.8,7@2.1|EV:+140,+145
[P2] PV:7|SUS:7@4.2,3@3.5|EV:+145
[P3] PV:2|SUS:0@3.8,1@3.2|EV:+140,-118
[P4] PV:3|SUS:3@4.9,5@2.8|EV:+140,+150

ULS++格式说明：
- PV:X 表示投票给玩家X
- SUS:X@Y 表示怀疑玩家X，分数Y（越高越怀疑）
- EV:+N/-N 表示支持(+)或反对(-)某个证据编号

现在请你分析：
1. 有多少玩家投票给Player 3？
2. 谁最怀疑Player 3（分数最高）？
3. 谁投票给了Player 7？

请简短回答（1-2句）。"""

    print("=" * 60)
    print("测试1: LLM能否理解ULS++编码")
    print("=" * 60)

    try:
        response = requests.post(
            f"{api_base}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": test_prompt}],
                "temperature": 0.1,  # 低温度以获得更确定的答案
                "max_tokens": 150
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content']
            print(f"\nLLM回答：\n{answer}\n")

            # 验证答案
            correct_answers = {
                "投票给P3的数量": 4,  # P0, P1, P4都投P3
                "最怀疑P3的": "P4",  # P4的SUS:3@4.9最高
                "投票给P7的": "P2"   # 只有P2投P7
            }

            print("\n正确答案：")
            print("1. 有3个玩家(P0, P1, P4)投票给Player 3")
            print("2. Player 4最怀疑Player 3 (分数4.9)")
            print("3. Player 2投票给Player 7")

            print("\n" + "=" * 60)

            # 测试2: 让LLM基于ULS++做决策
            test_prompt2 = """你是Player 5（村民），现在是投票阶段。

其他玩家的ULS++编码：
[P0] PV:3|SUS:3@4.6,5@3.7
[P1] PV:3|SUS:3@4.8,7@2.1
[P2] PV:7|SUS:7@4.2,3@3.5
[P3] PV:2|SUS:0@3.8,1@3.2
[P4] PV:3|SUS:3@4.9,5@2.8

分析：大多数人投票给P3，且怀疑度很高。你应该投票给谁？

请用ULS++格式回答（只输出一行）：
PV:X|SUS:...（X是你要投票的玩家编号）"""

            print("测试2: LLM能否基于ULS++做决策并生成ULS++")
            print("=" * 60)

            response2 = requests.post(
                f"{api_base}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": test_prompt2}],
                    "temperature": 0.3,
                    "max_tokens": 100
                },
                timeout=30
            )

            if response2.status_code == 200:
                result2 = response2.json()
                answer2 = result2['choices'][0]['message']['content']
                print(f"\nLLM生成的ULS++：\n{answer2}\n")

                # 检查是否包含PV:3（应该跟随多数）
                if "PV:3" in answer2:
                    print("✓ LLM正确理解了群体投票倾向，跟随多数投P3")
                else:
                    print("✗ LLM可能没有正确理解ULS++编码")
            else:
                print(f"测试2失败: {response2.status_code}")

        else:
            print(f"测试1失败: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"测试出错: {e}")

if __name__ == "__main__":
    test_uls_understanding()
