import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app import app, db, BRIEFING_OUTPUT_FOLDER
from models import Briefing, BriefingArticle, BriefingKeyword, BriefingSource, BriefingSystemLog
from utils import BriefingDocumentGenerator
from scraper_engine import engine

print('开始生成简报...')

task_id = '20260403171251'

with app.app_context():
    briefing = Briefing.query.filter_by(task_id=task_id).first()
    if not briefing:
        print('简报不存在')
        exit(1)
    
    briefing.status = 'running'
    briefing.start_time = datetime.now()
    db.session.commit()
    
    try:
        source_ids = json.loads(briefing.sources)
        keywords = [str(k) for k in json.loads(briefing.keywords)]
        
        # 获取关键词文本
        kw_objects = BriefingKeyword.query.filter(BriefingKeyword.id.in_([int(k) for k in keywords if k.isdigit()])).all()
        kw_texts = [kw.text for kw in kw_objects] if kw_objects else keywords
        
        print(f'关键词: {kw_texts}')
        
        sources = BriefingSource.query.filter(BriefingSource.id.in_([int(s) for s in source_ids if s.isdigit()])).all()
        print(f'数据源: {[s.name for s in sources]}')
        
        # engine is already imported from scraper_engine
        all_articles = []
        processed_urls = set()
        link_pool = []
        
        # 阶段1: 扫描首页
        print(f'\n阶段1: 扫描 {len(sources)} 个数据源...')
        for source in sources:
            try:
                result = engine.fetch_url(source.url, timeout=10)
                if result['status'] == 'success':
                    soup = BeautifulSoup(result['html'], 'lxml')
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        title = link.get_text(strip=True)
                        
                        if not href or href.startswith('javascript:') or len(title) < 4:
                            continue
                        
                        full_url = urljoin(source.url, href)
                        
                        # 关键词初筛
                        is_match = any(kw in title for kw in kw_texts)
                        
                        if is_match and full_url not in processed_urls:
                            processed_urls.add(full_url)
                            link_pool.append({
                                'url': full_url,
                                'title': title,
                                'source_name': source.name
                            })
                source_count = len([l for l in link_pool if l.get('source_name')==source.name])
                print(f'  {source.name}: 找到 {source_count} 条')
            except Exception as e:
                print(f'  {source.name}: 失败 - {e}')
        
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
                result = engine.fetch_url(item['url'], timeout=10)
                count += 1
                
                if count % 10 == 0:
                    print(f'  已抓取 {count}/{min(total_links, 50)}...')
                
                if result['status'] == 'success':
                    parsed = engine.parse_article(result['html'])
                    if parsed and parsed['content']:
                        full_text = parsed['content'] + parsed['title']
                        matched_kw = next((kw for kw in kw_texts if kw in full_text), None)
                        
                        if matched_kw:
                            all_articles.append({
                                'title': item['title'] or parsed['title'],
                                'content': parsed['content'],
                                'url': item['url'],
                                'source_name': item['source_name'],
                                'keyword': matched_kw
                            })
            except Exception:
                pass
        
        print(f'\n成功抓取 {len(all_articles)} 篇相关文章')
        
        # 阶段3: 保存结果
        if all_articles:
            unique_articles = []
            seen_titles = set()
            for art in all_articles:
                if art['title'] not in seen_titles:
                    seen_titles.add(art['title'])
                    unique_articles.append(art)
            
            print(f'去重后: {len(unique_articles)} 篇')
            
            output_filename = f"{briefing.title}.docx"
            output_path = os.path.join(BRIEFING_OUTPUT_FOLDER, output_filename)
            BriefingDocumentGenerator.create_word_document(unique_articles, output_path)
            briefing.docx_path = output_path
            
            for article in unique_articles:
                art = BriefingArticle(
                    briefing_id=briefing.id,
                    title=article['title'],
                    content=article['content'],
                    source_name=article['source_name'],
                    source_url=article['url'],
                    keyword=article['keyword'],
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
        
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()
        briefing.status = 'failed'
        briefing.error_message = str(e)
        db.session.commit()
