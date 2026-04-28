import os
import sys
import json
import argparse
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ================= 配置区 =================
API_KEY = os.getenv("DASHSCOPE_API_KEY", "EMPTY")
API_BASE = "http://123.57.212.178:3333/v1"
DEFAULT_MODEL = "gpt-4o-2024-11-20"
API_CONCURRENCY = 1 # 多线程并发数
MAX_NEW_TOKENS = 16392   # 最大生成token数

# 默认配置
DEFAULT_INPUT_DIR = "/mnt/workspace/chenming.hyc/dj_eval/data/gpt-4o_test"
DEFAULT_OUTPUT_DIR = "/mnt/workspace/chenming.hyc/dj_eval/data/gpt-4o_test"

def get_user_input(data):
    """
    从数据中提取用户输入内容
    支持两种格式:
    1. 标准格式: messages数组，取第一个user角色的content
    2. 简化格式: 直接有user字段
    """
    # 尝试从messages数组中获取
    messages = data.get("messages", [])
    for msg in messages:
        if msg.get("role") == "user":
            return msg.get("content", "")
    
    # 回退到直接user字段
    return data.get("user", "")


def call_model_once(client, target_model_name, messages, temperature=0.0):
    """
    调用模型一次，返回生成文本
    """
    completion = client.chat.completions.create(
        model=target_model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=MAX_NEW_TOKENS,
        stream=False,
        # extra_body={"enable_thinking": False}
    )
    return completion.choices[0].message.content


def process_single_sample(args):
    """
    处理单条数据的函数，将被放入线程池中并发执行。
    支持运行k次，当k>1时predict字段为列表，k=1时为单个字符串（向后兼容）。
    """
    data_line, client, target_model_name, num_runs = args
    try:
        data = json.loads(data_line)
        
        # 提取用户输入的内容
        user_input = get_user_input(data)
            
        messages = [
            {"role": "user", "content": user_input.strip()}
        ]

        if num_runs == 1:
            # 单次运行：贪婪搜索，temperature=0.0，结果为字符串
            generated_text = call_model_once(client, target_model_name, messages, temperature=0.0)
            data["predict"] = generated_text
        else:
            # 多次运行：使用temperature>0以获得多样性，结果为列表
            predictions = []
            for _ in range(num_runs):
                generated_text = call_model_once(client, target_model_name, messages, temperature=0.7)
                predictions.append(generated_text)
            data["predict"] = predictions
        
        return data
        
    except Exception as e:
        print(f"\n请求出错: {e}")
        data = json.loads(data_line) if isinstance(data_line, str) else data_line
        error_msg = f"ERROR: {str(e)}"
        data["predict"] = error_msg if num_runs == 1 else [error_msg] * num_runs
        return data



def process_file(input_file, output_file, client, target_model_name, num_runs=1, max_samples=None):
    """
    处理单个JSONL文件
    """
    run_info = f" (k={num_runs})" if num_runs > 1 else ""
    print(f"📂 正在读取数据集: {input_file}{run_info}")
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    if max_samples is not None:
        lines = lines[:max_samples]
    
    total_samples = len(lines)
    print(f"✅ 共读取到 {total_samples} 条数据。准备开始并发推理...")
    
    results = []
    
    # 准备参数列表
    args_list = [(line, client, target_model_name, num_runs) for line in lines]
    
    # 启动多线程并发请求
    with ThreadPoolExecutor(max_workers=API_CONCURRENCY) as executor:
        # 提交所有任务
        futures = [executor.submit(process_single_sample, args) for args in args_list]
        
        # 使用 tqdm 显示进度条
        for future in tqdm(as_completed(futures), total=total_samples, desc=f"处理 {input_file.name}"):
            results.append(future.result())
            
    # 保存结果
    print(f"💾 推理完成！正在保存结果到: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for res in results:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
    
    return total_samples


# ================= 主流程 =================
def main():
    parser = argparse.ArgumentParser(description="使用API进行批量推理")
    parser.add_argument("--model-name", type=str, default=DEFAULT_MODEL, help=f"模型名称 (默认: {DEFAULT_MODEL})")
    parser.add_argument("--api-base", type=str, default=API_BASE, help=f"API地址 (默认: {API_BASE})")
    parser.add_argument("--input-dir", type=str, default=DEFAULT_INPUT_DIR, help=f"输入目录 (默认: {DEFAULT_INPUT_DIR})")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help=f"输出目录 (默认: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--file", type=str, default=None, help="指定单个文件处理 (可选)")
    parser.add_argument("-k", "--num-runs", type=int, default=1, help="每条数据推理k次，k>1时predict字段为列表 (默认: 1)")
    parser.add_argument("--skip-existing", action="store_true", help="跳过已存在的输出文件 (默认: False)")
    parser.add_argument("--max-samples", type=int, default=None, help="每个文件只处理前N条数据 (默认: 全部)")
    
    args = parser.parse_args()
    
    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=API_KEY,
        base_url=args.api_base,
    )
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    num_runs = args.num_runs
    
    if num_runs < 1:
        print("❌ --num-runs (-k) 必须 >= 1")
        sys.exit(1)
    
    if num_runs > 1:
        print(f"🔄 每条数据将推理 {num_runs} 次，predict字段将存储为列表")
    
    # 如果指定了单个文件
    if args.file:
        input_file = input_dir / args.file
        if not input_file.exists():
            print(f"❌ 文件不存在: {input_file}")
            sys.exit(1)
        output_file = output_dir / args.file
        if args.skip_existing and output_file.exists():
            print(f"⏭️  跳过已存在的文件: {output_file}")
            sys.exit(0)
        process_file(input_file, output_file, client, args.model_name, num_runs, args.max_samples)
    else:
        # 处理所有jsonl文件
        jsonl_files = sorted(input_dir.glob("*.jsonl"))
        if not jsonl_files:
            print(f"❌ 在 {input_dir} 中没有找到 .jsonl 文件")
            sys.exit(1)
        
        # 过滤掉已存在的文件（如果启用skip-existing）
        files_to_process = []
        skipped_files = []
        for input_file in jsonl_files:
            output_file = output_dir / input_file.name
            if args.skip_existing and output_file.exists():
                skipped_files.append(input_file.name)
            else:
                files_to_process.append(input_file)
        
        if skipped_files:
            print(f"⏭️  跳过 {len(skipped_files)} 个已存在的文件: {', '.join(skipped_files)}")
        
        if not files_to_process:
            print("✅ 没有新文件需要处理")
            sys.exit(0)
        
        print(f"🚀 找到 {len(files_to_process)} 个文件需要处理")
        total_samples = 0
        
        for input_file in files_to_process:
            output_file = output_dir / input_file.name
            samples = process_file(input_file, output_file, client, args.model_name, num_runs, args.max_samples)
            total_samples += samples
            print()
        
        print(f"🎉 所有任务处理完毕！共处理 {len(files_to_process)} 个文件，{total_samples} 条数据。")
        print(f"📁 输出目录: {output_dir}")

if __name__ == "__main__":
    main()