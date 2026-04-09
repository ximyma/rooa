import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app import app, db, BRIEFING_OUTPUT_FOLDER
from models import Briefing, BriefingArticle, BriefingKeyword, BriefingSource
from utils import BriefingDocumentGenerator
from scraper_engine import engine

print('开始生成经济金融热点简报...')

task_id = datetime.now().strftime('%Y%m%d%H%M%S')

with app.app_context():
    # 经济金融关键词
    finance_keywords = [
        '股市', 'A股', '港股', '美股', '大盘', '指数',
        '涨停', '跌停', '牛市', '熊市',
        '央行', '美联储', '加息', '降息', '降准',
        '汇率', '人民币', '美元',
        '黄金', '原油', '大宗商品',
        '房地产', '楼市', '房价',
        '银行', '保险', '证券', '基金', '理财',
        '债券', 'IPO', '上市',
        'GDP', 'CPI', '通胀',
        '就业', '消费', '投资',
        '新能源', '光伏', '锂电',
        '人工智能', '芯片', '半导体'
    ]
    
    # 获取关键词对象
    kw_objects = BriefingKeyword.query.filter(BriefingKeyword.text.in_(finance_keywords)).all()
    kw_ids = [str(k.id) for k in kw_objects]
    kw_texts = [k.text for k in kw_objects]
    
    print(f'筛选关键词: {len(kw_texts)} 个')
    
    # 金融数据源（优先主流财经媒体）
    priority_sources = [
        '新浪财经', '网易财经', '腾讯财经', '搜狐财经', '凤凰财经',
        '东方财富', '同花顺', '雪球', '财联社',
        '证券时报', '上海证券报', '中国证券报',
        '经济观察报', '第一财经', '21世纪经济报道',
        '央行官网', '证监会', '银保监会'
    ]
    
    src_objects = BriefingSource.query.filter(BriefingSource.name.in_(priority_sources)).all()
    src_ids = [str(s.id) for s in src_objects]
    
    print(f'数据源数量: {len(src_objects)} 个')
    for s in src_objects:
        print(f'  - {s.name}')
    
    # 创建简报记录
    date = datetime.now().strftime('%Y%m%d')
    title = f'经济金融热点简报_{date}'
    
    briefing = Briefing(
        task_id=task_id,
        title=title,
        keywords=json.dumps(kw_ids, ensure_ascii=False),
        sources=json.dumps(src_ids, ensure_ascii=False),
        target_date=date,
        status='running',
        user_id=1
    )
    db.session.add(briefing)
    db.session.commit()
    
    briefing.start_time = datetime.now()
    
    try:
        all_articles = []
        processed_urls = set()
        link_pool = []
        
        # 阶段1: 扫描首页
        print(f'\n阶段1: 扫描 {len(src_objects)} 个数据源...')
        for source in src_objects:
            try:
                result = engine.fetch_url(source.url, timeout=8)
                if result['status'] == 'success':
                    soup = BeautifulSoup(result['html'], 'lxml')
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        title_text = link.get_text(strip=True)
                        
                        if not href or href.startswith('javascript:') or len(title_text) < 5:
                            continue
                        
                        full_url = urljoin(source.url, href)
                        
                        # 关键词匹配
                        matched_kws = []
                        priority = 0
                        
                        for kw in finance_keywords:
                            if kw in title_text:
                                matched_kws.append(kw)
                                # 市场热点优先级更高
                                if kw in ['股市', 'A股', '涨停', '跌停', '大盘']:
                                    priority += 3
                                elif kw in ['央行', '美联储', '加息', '降息']:
                                    priority += 3
                                elif kw in ['房地产', '楼市', '房价']:
                                    priority += 2
                                else:
                                    priority += 1
                        
                        if matched_kws and full_url not in processed_urls:
                            processed_urls.add(full_url)
                            link_pool.append({
                                'url': full_url,
                                'title': title_text,
                                'source_name': source.name,
                                'keywords': matched_kws,
                                'priority': min(priority, 5)
                            })
                
                source_count = len([l for l in link_pool if l.get('source_name')==source.name])
                print(f'  {source.name}: 找到 {source_count} 条')
            except Exception as e:
                print(f'  {source.name}: 失败 - {e}')
        
        # 按优先级排序
        link_pool.sort(key=lambda x: x['priority'], reverse=True)
        
        total_links = len(link_pool)
        print(f'\n共发现 {total_links} 篇疑似文章')
        
        if total_links == 0:
            briefing.status = 'completed'
            briefing.article_count = 0
            db.session.commit()
            print('未发现相关文章')
            exit(0)
        
        # 阶段2: 并发抓取正文
        print(f'\n阶段2: 抓取正文 (最多50篇)...')
        count = 0
        for item in link_pool[:50]:
            try:
                result = engine.fetch_url(item['url'], timeout=8)
                count += 1
                
                if count % 10 == 0:
                    print(f'  已抓取 {count}/{min(total_links, 50)}...')
                
                if result['status'] == 'success':
                    parsed = engine.parse_article(result['html'])
                    if parsed and parsed['content'] and len(parsed['content']) > 100:
                        all_articles.append({
                            'title': item['title'] or parsed['title'],
                            'content': parsed['content'],
                            'url': item['url'],
                            'source_name': item['source_name'],
                            'keywords': item['keywords'],
                            'priority': item['priority']
                        })
            except Exception:
                pass
        
        print(f'\n成功抓取 {len(all_articles)} 篇相关文章')
        
        # 阶段3: 保存结果
        if all_articles:
            # 去重
            unique_articles = []
            seen_titles = set()
            for art in all_articles:
                if art['title'] not in seen_titles:
                    seen_titles.add(art['title'])
                    unique_articles.append(art)
            
            # 按优先级排序
            unique_articles.sort(key=lambda x: x['priority'], reverse=True)
            
            print(f'去重后: {len(unique_articles)} 篇')
            print(f'高优先级(≥3): {len([a for a in unique_articles if a["priority"]>=3])} 篇')
            
            # 生成Word文档
            output_filename = f"{briefing.title}.docx"
            output_path = os.path.join(BRIEFING_OUTPUT_FOLDER, output_filename)
            
            # 转换格式用于文档生成
            doc_articles = []
            for art in unique_articles[:40]:  # 最多40篇
                doc_articles.append({
                    'title': art['title'],
                    'content': art['content'],
                    'url': art['url'],
                    'source_name': art['source_name'],
                    'keyword': ', '.join(art['keywords'][:3])
                })
            
            BriefingDocumentGenerator.create_word_document(doc_articles, output_path)
            briefing.docx_path = output_path
            
            # 保存到数据库
            for article in unique_articles[:40]:
                art = BriefingArticle(
                    briefing_id=briefing.id,
                    title=article['title'],
                    content=article['content'],
                    source_name=article['source_name'],
                    source_url=article['url'],
                    keyword=', '.join(article['keywords'][:3]),
                    word_count=len(article['content'])
                )
                db.session.add(art)
            
            briefing.article_count = len(unique_articles[:40])
            print(f'\n文档已保存: {output_path}')
        
        briefing.status = 'completed'
        briefing.end_time = datetime.now()
        briefing.duration = (briefing.end_time - briefing.start_time).seconds if briefing.start_time else 0
        db.session.commit()
        
        print(f'\n✅ 简报生成完成！')
        print(f'文章数: {briefing.article_count}')
        print(f'任务ID: {task_id}')
        
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()
        briefing.status = 'failed'
        briefing.error_message = str(e)
        db.session.commit()
