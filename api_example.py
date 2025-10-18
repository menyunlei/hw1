import os
from anthropic import Anthropic

# 使用环境变量初始化客户端
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_AUTH_TOKEN"),
    base_url=os.getenv("ANTHROPIC_BASE_URL")
)

# 发送消息到Claude
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",  # 确保模型名称正确，根据API文档调整
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude! 请介绍一下你自己。"}
    ]
)

# 打印响应
print(message.content)