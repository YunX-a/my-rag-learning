# app/services/agent_service.py
from typing import AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from app.core.config import settings
from app.services.rag_service import get_retriever, reciprocal_rank_fusion
from app.services.es_service import search_keyword
from langchain_core.documents import Document
import json

# --- 1. 定义工具 (Tools) ---

@tool
def search_knowledge_base(query: str) -> str:
    """
    这是一个知识库搜索工具。
    当用户询问关于[编程、计算机、Java、Python、Linux]等技术问题时，务必使用此工具。
    输入应该是用户完整的问题或提取的关键查询语句。
    返回的是相关的文档片段。
    """
    print(f"Agent 正在调用工具: search_knowledge_base -> {query}")
    
    # 复用 RAG 的混合检索逻辑
    # A. Milvus
    retriever = get_retriever(k=4)
    milvus_docs = retriever.invoke(query)
    
    # B. ES
    es_hits = search_keyword(query, k=4)
    es_docs = [
        Document(page_content=hit["_source"]["content"], metadata=hit["_source"]) 
        for hit in es_hits
    ]
    
    # C. Fusion
    final_docs = reciprocal_rank_fusion([milvus_docs, es_docs], k=60)
    
    # 格式化返回给 Agent
    if not final_docs:
        return "知识库中未找到相关内容。"
        
    return "\n\n".join([f"[片段{i+1}]: {d.page_content}" for i, d in enumerate(final_docs[:4])])

# --- 2. 初始化 Agent ---

def get_agent_executor():
    # 定义工具集
    tools = [search_knowledge_base]
    
    # 定义 LLM (必须支持 Tool Calling)
    llm = ChatOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL_NAME,
        temperature=0.1
    )
    
    # 定义 Prompt
    # 这是一个标准的 Agent Prompt，包含 System 指令和占位符
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个智能技术顾问。你拥有一个强大的知识库工具。请根据用户的提问，判断是否需要查询知识库。如果用户只是打招呼（如'你好'），请直接回复。如果涉及技术问题，请调用工具。"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"), # 关键：留给 Agent 思考和记录工具调用过程的地方
    ])
    
    # 创建 Agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # 创建执行器
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 3. 流式对话接口 ---
async def stream_agent_chat(question: str) -> AsyncGenerator[str, None]:
    agent_executor = get_agent_executor()
    
    # LangChain 的 Agent 流式输出比较复杂，这里用 astream_events 或 astream
    # 为了简化适配你的前端，我们只输出最终答案的 token
    
    try:
        # astream 返回的是一个个 chunk，包含了思考过程和最终答案
        # 这里的处理稍微有点 trick，我们需要过滤出最终的 answer
        async for event in agent_executor.astream_events(
            {"input": question}, 
            version="v1"
        ):
            kind = event["event"]
            
            # 当 LLM 开始输出最终回答时 (on_chat_model_stream)
            if kind == "on_chat_model_stream":
                # CAN: 修复点 - 使用 .get() 安全访问，并通过 if 判断确保 chunk 存在
                data = event.get("data", {})
                chunk = data.get("chunk")
                
                if chunk:
                    content = chunk.content
                    if content:
                        yield content
                    
    except Exception as e:
        print(f"Agent Error: {e}")
        yield f"Agent 运行出错: {str(e)}"