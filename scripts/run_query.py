# query_test.py
import asyncio
import os
from app.core.config import settings
from app.services.rag_service import stream_rag_answer

# 强制设置 env (防止某些环境没加载到)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

async def main():
    # 这里的 question 最好跟你刚才上传的 PDF 内容相关
    question = "在这份指南中，计算机大厂面试主要看重什么？" 
    
    print(f"\n>>>  提问: {question}")
    print(">>>  正在思考...\n")
    print("-" * 50)

    try:
        async for chunk in stream_rag_answer(
            question=question,
            llm_api_key=settings.DEEPSEEK_API_KEY,
            llm_base_url=settings.LLM_BASE_URL,
            llm_model=settings.LLM_MODEL_NAME
        ):
            # flush=True 确保流式输出能实时显示
            print(chunk, end="", flush=True)
    except Exception as e:
        print(f"\n 测试出错: {e}")
    
    print("\n" + "-" * 50)
    print(">>>  回答结束")

if __name__ == "__main__":
    # 检查 Key 是否配置
    if not settings.DEEPSEEK_API_KEY.get_secret_value():
        print(" 警告: 未配置 DEEPSEEK_API_KEY，请检查 .env 文件！")
    else:
        asyncio.run(main())