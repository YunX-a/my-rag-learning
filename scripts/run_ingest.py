# ingest_test.py
import os
from app.services.ingestion_service import process_and_embed_document

# 创建一个假的 PDF 用于测试
def create_dummy_pdf(filename="test_doc.pdf"):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Hello, this is a test document for RAG ingestion.")
    c.drawString(100, 730, "Milvus is a vector database.")
    c.drawString(100, 710, "Minio is an object storage.")
    c.save()
    print(f"已创建测试文件: {filename}")
    return filename

if __name__ == "__main__":
    # 1. 准备测试文件
    pdf_path = "./data/计算机大厂求职面试指南.pdf"
    if not os.path.exists(pdf_path):
        # 如果没有现成的 PDF，尝试生成一个（需要 reportlab 库）
        # 或者你可以手动放一个 pdf 到根目录
        try:
            create_dummy_pdf(pdf_path)
        except ImportError:
            print("请在根目录放一个名为 'test_doc.pdf' 的文件进行测试")
            exit(1)

    # 2. 执行摄取流程
    print(">>> 开始测试文档摄取流程...")
    try:
        count = process_and_embed_document(pdf_path)
        print(f">>> 测试结束。成功处理了 {count} 个文本块。")
    except Exception as e:
        print(f"!!! 测试失败: {e}")