import os
from dashscope import Generation
import dashscope
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置DashScope API基础URL
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

def test_llm_connection():
    """测试LLM连接功能"""
    try:
        logger.info("开始测试LLM连接...")
        
        # 设置API密钥
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            logger.error("未找到DASHSCOPE_API_KEY环境变量")
            return False
            
        logger.info(f"使用API密钥: {api_key[:10]}...")  # 只显示前10位用于确认
        
        # 构建测试消息
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "你是谁？"},
        ]
        
        logger.info("发送请求到DashScope API...")
        
        # 调用Generation API
        response = Generation.call(
            api_key=api_key,
            model="qwen3-max",
            messages=messages,
            result_format="message",
            timeout=120  # 增加超时时间到120秒
        )
        
        # 检查响应
        if response.status_code == 200:
            logger.info("LLM API调用成功!")
            logger.info(f"响应内容: {response.output.choices[0].message.content}")
            return True
        else:
            logger.error(f"LLM API调用失败，状态码: {response.status_code}")
            logger.error(f"错误信息: {response.message}")
            return False
            
    except Exception as e:
        logger.error(f"测试LLM连接时发生异常: {e}")
        return False

if __name__ == "__main__":
    success = test_llm_connection()
    if success:
        print("✅ LLM连接测试成功!")
    else:
        print("❌ LLM连接测试失败!")