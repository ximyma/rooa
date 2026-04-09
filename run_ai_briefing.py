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

print('开始生成AI与数字化转型专题简报...')

task_id = datetime.now().strftime('%Y%m%d%H%M%S')

with app.app_context():
    # 只选择AI和数字化转型相关的关键词
    target_keywords = [
        '人工智能', '智能制造', '企业数字化', '数字化转型', '数字经济', 
        '数字中国', '工业互联网', '大数据', '云计算', '物联网', 
        '5G应用', '智慧工厂', '产业升级'
    ]
    
    # 只选择江西赣州相关的地域关键词
    location_keywords = ['江西', '赣州', '南昌', '赣江新区']
    
    # 政策相关
    policy_keywords = ['政策', '规划', '项目', '投资', '补贴']
    
    # 合并所有要搜索的关键词
    all_search_keywords = target_keywords + location_keywords + policy_keywords
    
    # 获取关键词对象
    kw_objects = BriefingKeyword.query.filter(BriefingKeyword.text.in_(all_search_keywords)).all()
    kw_ids = [str(k.id) for k in kw_objects]
    kw_texts = [k.text for k in kw_objects]
    
    print(f'筛选关键词: {kw_texts}')
    
    # 选择重点数据源（优先江西赣州本地源）
    priority_sources = [
        '江西省人民政府', '赣州市人民政府', '江西省工信厅', 
        '赣州市工信局', '江西省发改委', '工信部', '国家发改委',
        '大江网', '客家新闻网', '新华网', '中国新闻网'
    ]
    
    src_objects = BriefingSource.query.filter(BriefingSource.name.in_(priority_sources)).all()
    src_ids = [str(s.id) for s in src_objects]
    
    print(f'数据源数量: {len(src_objects)}')
    for s in src_objects:
        print(f'  - {s.name}')
    
    # 创建简报记录
    date = datetime.now().strftime('%Y%m%d')
    title = f'AI与数字化转型政策简报_{date}'
    
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
                result = engine.fetch_url(source.url, timeout=10)
                if result['status'] == 'success':
                    soup = BeautifulSoup(result['html'], 'lxml')
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        title_text = link.get_text(strip=True)
                        
                        if not href or href.startswith('javascript:') or len(title_text) < 4:
                            continue
                        
                        full_url = urljoin(source.url, href)
                        
                        # 关键词匹配 - 必须包含AI/数字化相关或地域相关
                        is_tech_match = any(kw in title_text for kw in target_keywords)
                        is_location_match = any(kw in title_text for kw in location_keywords)
                        is_policy_match = any(kw in title_text for kw in policy_keywords)
                        
                        # 优先匹配：技术+地域，或技术+政策
                        priority = 0
                        if is_tech_match and is_location_match:
                            priority = 3  # 最高优先级：技术+地域
                        elif is_tech_match and is_policy_match:
                            priority = 2  # 高优先级：技术+政策
                        elif is_tech_match:
                            priority = 1  # 中等优先级：仅技术
                        elif is_location_match and is_policy_match:
                            priority = 1  # 中等优先级：地域+政策
                        
                        if priority > 0 and full_url not in processed_urls:
                            processed_urls.add(full_url)
                            link_pool.append({
                                'url': full_url,
                                'title': title_text,
                                'source_name': source.name,
                                'priority': priority
                            })
                
                source_count = len([l for l in link_pool if l.get('source_name')==source.name])
                print(f'  {source.name}: 找到 {source_count} 条')
            except Exception as e:
                print(f'  {source.name}: 失败 - {e}')
        
        # 按优先级排序
        link_pool.sort(key=lambda x: x['priority'], reverse=True)
        
        total_links = len(link_pool)
        print(f'\n共发现 {total_links} 篇疑似文章（已按优先级排序）')
        
        if total_links == 0:
            briefing.status = 'completed'
            briefing.article_count = 0
            db.session.commit()
            print('未发现相关文章')
            exit(0)
        
        # 阶段2: 并发抓取正文
        print(f'\n阶段2: 抓取正文 (最多80篇)...')
        count = 0
        for item in link_pool[:80]:
            try:
                result = engine.fetch_url(item['url'], timeout=10)
                count += 1
                
                if count % 10 == 0:
                    print(f'  已抓取 {count}/{min(total_links, 80)}...')
                
                if result['status'] == 'success':
                    parsed = engine.parse_article(result['html'])
                    if parsed and parsed['content']:
                        full_text = (parsed['content'] + ' ' + parsed['title']).lower()
                        
                        # 确定匹配的关键词
                        matched_kws = []
                        for kw in target_keywords:
                            if kw in item['title'] or kw in parsed['title'] or kw in parsed['content']:
                                matched_kws.append(kw)
                        
                        # 只要有技术关键词匹配就收录
                        if matched_kws:
                            all_articles.append({
                                'title': item['title'] or parsed['title'],
                                'content': parsed['content'],
                                'url': item['url'],
                                'source_name': item['source_name'],
                                'keywords': matched_kws,
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
            print(f'高优先级文章(3级): {len([a for a in unique_articles if a["priority"]==3])} 篇')
            print(f'中高优先级文章(2级): {len([a for a in unique_articles if a["priority"]==2])} 篇')
            
            # 生成Word文档
            output_filename = f"{briefing.title}.docx"
            output_path = os.path.join(BRIEFING_OUTPUT_FOLDER, output_filename)
            
            # 转换格式用于文档生成
            doc_articles = []
            for art in unique_articles:
                doc_articles.append({
                    'title': art['title'],
                    'content': art['content'],
                    'url': art['url'],
                    'source_name': art['source_name'],
                    'keyword': ', '.join(art['keywords'][:3])  # 取前3个关键词
                })
            
            BriefingDocumentGenerator.create_word_document(doc_articles, output_path)
            briefing.docx_path = output_path
            
            # 保存到数据库
            for article in unique_articles:
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
            
            briefing.article_count = len(unique_articles)
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
