#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能并发抓取引擎 - 简报系统专用
支持多线程、反爬虫策略、超时控制
"""
import requests
from bs4 import BeautifulSoup
import time
import random
import threading
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


class ScraperEngine:
    """高性能并发抓取引擎"""
    
    def __init__(self, max_workers=15):
        # 线程池大小，建议10-20，过大容易被封IP
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.session = requests.Session()
        
        # 请求头池（模拟不同浏览器）
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:88.0) Gecko/20100101 Firefox/88.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        # 线程安全的计数器
        self.request_count = 0
        self.lock = threading.Lock()

    def get_headers(self):
        """生成随机请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }

    def fetch_url(self, url, timeout=8):
        """
        抓取单个URL
        :param url: 目标地址
        :param timeout: 超时时间（秒）
        """
        try:
            # 随机延迟 0.3s - 1.0s，避免请求过快被封
            time.sleep(random.uniform(0.3, 1.0))
            
            response = self.session.get(
                url, 
                headers=self.get_headers(), 
                timeout=timeout,
                verify=False,  # 跳过SSL验证，防止证书错误
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # 自动检测编码
                if not response.encoding or response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding
                return {'status': 'success', 'html': response.text, 'url': url}
            else:
                return {'status': 'error', 'message': f'Status {response.status_code}', 'url': url}
                
        except requests.Timeout:
            return {'status': 'error', 'message': 'Timeout', 'url': url}
        except requests.RequestException as e:
            return {'status': 'error', 'message': str(e), 'url': url}
        except Exception as e:
            return {'status': 'error', 'message': f'Unknown: {str(e)}', 'url': url}

    def parse_article(self, html, config=None):
        """
        解析文章内容 (使用BeautifulSoup)
        :param html: 网页源码
        :param config: 解析配置 (选择器)
        """
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'lxml')  # lxml解析器速度更快
        
        # 1. 提取标题
        title = ''
        title_tag = soup.find('h1')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # 2. 提取正文 (简单的通用提取策略)
        content = ''
        # 优先查找文章主体标签
        article = soup.find('article') or soup.find('div', class_='content') or soup.find('div', id='content')
        
        if article:
            # 移除脚本和样式
            for script in article(["script", "style", "noscript"]):
                script.decompose()
            content = article.get_text(separator='\n', strip=True)
        else:
            # 后备方案：提取所有段落
            paragraphs = soup.find_all('p')
            content = '\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])

        # 清洗数据
        if len(content) < 100:  # 内容太短视为无效
            return None
            
        return {
            'title': title,
            'content': content[:5000]  # 截取前5000字
        }

    def batch_crawl(self, url_list, callback=None):
        """
        并发抓取多个URL
        :param url_list: URL列表
        :param callback: 处理成功结果的回调函数
        :return: 结果列表
        """
        results = []
        future_to_url = {
            self.executor.submit(self.fetch_url, url): url 
            for url in url_list
        }
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                if result['status'] == 'success' and callback:
                    parsed = callback(result['html'])
                    if parsed:
                        results.append(parsed)
            except Exception as exc:
                logger.warning(f"URL {url} generated an exception: {exc}")
        
        return results


# 全局单例，避免重复创建线程池
engine = ScraperEngine()
