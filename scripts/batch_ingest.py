import os
import sys
import time

# --- 将项目根目录加入 Python 路径 ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ingestion_service import process_and_embed_document

def batch_ingest_recursive(root_folder: str = "data/pdfs"):
    """
    递归遍历文件夹及其所有子文件夹，处理所有 PDF 文件
    """
    # 1. 检查根目录是否存在
    if not os.path.exists(root_folder):
        print(f" 错误：文件夹 '{root_folder}' 不存在！")
        return

    print(f" 正在递归扫描 '{root_folder}' 下的所有 PDF 文件...")
    
    # 2. 使用 os.walk 收集所有 PDF 文件的完整路径
    pdf_files = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                # 组合成完整路径
                full_path = os.path.join(root, file)
                pdf_files.append(full_path)

    total_files = len(pdf_files)
    
    if total_files == 0:
        print(f"  未找到任何 PDF 文件。")
        return

    print(f" 共发现 {total_files} 个 PDF 文件，准备开始处理...")
    print("=" * 60)

    success_count = 0
    fail_count = 0
    start_time = time.time()

    # 3. 循环处理
    for index, file_path in enumerate(pdf_files):
        # 获取相对路径，打印出来好看一点 (例如: subfolder/book.pdf)
        relative_name = os.path.relpath(file_path, root_folder)
        current_num = index + 1
        
        print(f"[{current_num}/{total_files}] 处理中: {relative_name} ... ", end="", flush=True)

        try:
            chunks = process_and_embed_document(file_path)
            
            if chunks > 0:
                print(f" 成功 ({chunks} 片段)")
                success_count += 1
            else:
                print(f"  警告 (内容为空)")
                fail_count += 1
                
        except Exception as e:
            print(f" 失败: {str(e)}")
            fail_count += 1

    # 4. 总结
    duration = time.time() - start_time
    print("=" * 60)
    print(f" 递归批量任务结束！耗时: {duration:.2f} 秒")
    print(f" 统计: 成功 {success_count} | 失败 {fail_count} | 总计 {total_files}")
    print(" 知识库更新完毕！")

if __name__ == "__main__":
    TARGET_DIR = "data/pdfs"
    if len(sys.argv) > 1:
        TARGET_DIR = sys.argv[1]

    batch_ingest_recursive(TARGET_DIR)