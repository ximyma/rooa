import pandas as pd
import requests
import re
import time
import random
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import warnings
from bs4 import BeautifulSoup
import xlsxwriter 

# 禁用警告
warnings.filterwarnings('ignore')

# 线程安全打印锁
print_lock = threading.Lock()

class Config:
    MAX_RETRIES = 3
    TIMEOUT = 10
    WORKERS = 8
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15'
    ]
    OUTPUT_COLUMNS = [
        '序号', '网址', '栏目名称', '栏目分类',
        '更新期限', '期限', '最大日期',
        '连续不更新天数', '是否逾期', '记录时间'
    ]

headers = {
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'keep-alive',
    'Accept-Encoding': 'gzip, deflate'
}

def get_page_text(url: str) -> str:
    """带智能重试的页面获取函数"""
    headers['User-Agent'] = random.choice(Config.USER_AGENTS)
    for retry in range(Config.MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=Config.TIMEOUT)
            response.raise_for_status()
            
            # 反爬检测
            if any(keyword in response.text for keyword in ['访问过于频繁', '机器人']):
                raise requests.exceptions.RequestException("触发反爬机制")
                
            return response.text
        except requests.exceptions.RequestException as e:
            if retry == Config.MAX_RETRIES - 1:
                raise
            sleep_time = 2 ** retry + random.uniform(0, 1)
            with print_lock:
                tqdm.write(f"! 重试 {url[:30]}... 等待 {sleep_time:.1f}s", file=sys.stdout)
            time.sleep(sleep_time)
    return ""

def process_data(args: tuple) -> tuple:
    """处理单个URL任务"""
    index, url, row = args
    start_time = time.time()
    status = "✅"
    error_msg = ""
    result = None
    
    try:
        text = get_page_text(url)
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.body.text
        dates = pd.to_datetime(
            re.findall(r'\d{4}-\d{2}-\d{2}', text),
            errors='coerce'
        )
        valid_dates = dates[~dates.isnull()]
        max_date = valid_dates.max() if not valid_dates.empty else pd.NaT
        
        result = {
            '序号': index + 1,
            '网址': url,
            '栏目名称': row['栏目名称'],
            '栏目分类': row['栏目分类'],
            '更新期限': row['更新期限'],
            '期限': row['期限'],
            '最大日期': max_date
        }
    except Exception as e:
        status = "❌"
        error_msg = f"{str(e)[:50]}..." if len(str(e)) > 50 else str(e)
        result = {
            '序号': index + 1,
            '网址': url,
            **{col: row[col] for col in ['栏目名称', '栏目分类', '更新期限', '期限']},
            '最大日期': pd.NaT
        }
    finally:
        elapsed = time.time() - start_time
        with print_lock:
            tqdm.write(f"{status} 第 {index+1:03d} 条 | 耗时 {elapsed:.1f}s | {error_msg}", file=sys.stdout)

    return (index, result)

def main():
    # 读取数据
    df_url = pd.read_excel('url_2.xlsx')
    total = len(df_url)
    start_time = time.time()  # 修复缺失的时间记录
    
    print(f"开始处理 {total} 条网址，线程数：{Config.WORKERS}")
    print("-" * 60)
    
    # 准备任务
    tasks = [(i, row['url'], row) for i, row in df_url.iterrows()]
    
    # 并发处理
    results = [None] * total  # 预分配结果列表
    with ThreadPoolExecutor(max_workers=Config.WORKERS) as executor:
        futures = {executor.submit(process_data, task): task for task in tasks}
        
        # 使用tqdm进度条
        with tqdm(total=total, desc="处理进度", unit="条", ncols=100) as pbar:
            for future in as_completed(futures):
                index = futures[future][0]
                try:
                    results[index] = future.result()
                except Exception as e:
                    pass  # 错误已在process_data处理
                pbar.update(1)
    
    # 构建结果DataFrame
    sorted_results = sorted([r for r in results if r is not None], key=lambda x: x[0])
    df_result = pd.DataFrame(
        data=[item[1] for item in sorted_results],
        columns=Config.OUTPUT_COLUMNS[:-3]
    )
    
    # 计算衍生字段
    now = datetime.now()
    # 确保最大日期是datetime类型
    df_result['最大日期'] = pd.to_datetime(df_result['最大日期'], errors='coerce')
    df_result['连续不更新天数'] = (now - df_result['最大日期']).dt.days.fillna(-1).astype(int)
    df_result['是否逾期'] = (df_result['期限'] < df_result['连续不更新天数']).fillna(False)
    df_result['记录时间'] = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # 生成文件名
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    output_path = f'result_{timestamp}.xlsx'
    
    # 输出Excel
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False)
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        # 设置格式
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        worksheet.set_column('G:G', 15, date_format)  # 最大日期列
        
        # 自动调整列宽
        for idx, col in enumerate(df_result.columns):
            try:
                max_len = max(df_result[col].apply(lambda x: len(str(x))).max(), len(col)) + 2
            except:
                max_len = len(col) + 5
            worksheet.set_column(idx, idx, max_len)
    
    # 最终统计
    success_count = df_result['最大日期'].isnull().sum()
    print("\n" + "-" * 60)
    print(f"处理完成！总耗时：{time.time() - start_time:.1f}秒")
    print(f"成功率：{success_count/total:.1%} ({success_count}/{total})")
    print(f"输出文件：{output_path}")
    print(f"最后更新：{now.strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == "__main__":
    main()