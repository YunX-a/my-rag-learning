# RAG 知识库助手 (RAG Knowledge Base Assistant)

基于 **FastAPI + LangChain + Milvus + Vue 3** 构建的企业级本地知识库问答系统。支持 PDF 文档上传、切片、向量化存储，并利用 LLM (DeepSeek) 进行基于上下文的智能问答。

## 功能特性

* **文档管理**：支持 PDF 文件上传、自动解析与切片。
* **混合检索**：基于 Milvus 的高性能向量检索，结合关键词匹配。
* **智能问答**：集成 DeepSeek LLM，支持流式输出 (Streaming) 打字机效果。
* **会话历史**：完整的对话记录存储，支持查看历史问答及参考来源。
* **来源溯源**：AI 回答时自动标注参考的文档及页码。
* **容器化部署**：提供完整的 Docker Compose 编排，一键启动所有服务。

## 技术栈

* **Backend**: Python 3.10, FastAPI, LangChain, SQLAlchemy
* **Frontend**: Vue 3, TypeScript, Vite, Element Plus
* **Vector DB**: Milvus (Standalone)
* **Database**: MySQL 8.0
* **Storage**: Minio (S3 Compatible)
* **Cache**: Redis
* **Model**: text2vec-base-chinese (Embedding), DeepSeek-Chat (LLM)

## 快速开始

### 1. 克隆项目

```bash
git clone [https://gitee.com/your-username/my-rag-learning.git](https://gitee.com/your-username/my-rag-learning.git)
cd my-rag-learning