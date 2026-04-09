import sys
sys.stdout.reconfigure(encoding="utf-8")
import json, os
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

os.chdir(r"C:\Users\Administrator\Desktop\ooa")
from app import app, db, BRIEFING_OUTPUT_FOLDER
from models import Briefing, BriefingArticle, BriefingSource
from utils import BriefingDocumentGenerator
from scraper_engine import engine

print("Generating domestic news briefing...")

task_id = datetime.now().strftime("%Y%m%d%H%M%S")
date_str = datetime.now().strftime("%Y%m%d")

with app.app_context():
    srcs = BriefingSource.query.filter(BriefingSource.id.in_(list(range(1, 26)))).all()
    print(f"Sources: {len(srcs)}")

    briefing = Briefing(
        task_id=task_id,
        title=f"24小时国内新闻热点简报_{date_str}",
        keywords=json.dumps(["国内", "中国", "经济", "政策", "就业"], ensure_ascii=False),
        sources=json.dumps([str(s.id) for s in srcs], ensure_ascii=False),
        target_date=date_str, status="running", user_id=1
    )
    db.session.add(briefing)
    db.session.commit()
    print(f"Briefing ID: {briefing.id}")

    all_articles = []
    processed = set()
    pool = []

    dkws = ["国内", "中国", "北京", "上海", "广州", "深圳", "经济", "政策", "国务院", "部委", "就业", "物价", "消费", "投资", "出口", "房地产", "楼市", "房价", "股市", "科技", "互联网", "数字经济", "教育", "医疗", "人工智能", "大模型", "江西", "赣州", "石城", "南昌", "创业板", "A股", "消费券", "养老金", "医保", "新基建", "数字中国", "中国制造"]
    exclude = ["特朗普", "美国", "伊朗", "以色列", "俄罗斯", "欧盟", "北约", "乌克兰", "关税", "制裁", "胡塞", "美方", "美伊", "美军", "英国", "法国", "德国", "日本", "中东", "欧洲", "教皇", "印度", "巴基斯坦", "沙特", "阿联酋", "也门", "美联社", "联合国", "WHO", "世卫"]

    print(f"Scanning {len(srcs)} sources...")
    for source in srcs:
        try:
            r = engine.fetch_url(source.url, timeout=8)
            if r["status"] == "success":
                soup = BeautifulSoup(r["html"], "lxml")
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    txt = link.get_text(strip=True)
                    if not href or len(txt) < 8:
                        continue
                    url = urljoin(source.url, href)
                    if url in processed:
                        continue
                    if any(e in txt for e in exclude):
                        continue
                    matched = [k for k in dkws if k in txt]
                    if matched:
                        processed.add(url)
                        pri = len(matched)
                        if source.name in ["人民日报", "新华网", "央视新闻", "中国政府网", "国家发改委", "工信部"]:
                            pri += 3
                        pool.append({"url": url, "title": txt, "src": source.name, "kws": matched, "pri": pri})
        except Exception as e:
            print(f"  {source.name}: {e}")

    print(f"Found {len(pool)} articles")
    pool.sort(key=lambda x: x["pri"], reverse=True)

    for item in pool[:50]:
        try:
            r = engine.fetch_url(item["url"], timeout=8)
            if r["status"] == "success":
                p = engine.parse_article(r["html"])
                if p and p.get("content") and len(p["content"]) > 100:
                    all_articles.append({
                        "title": item["title"] or p["title"],
                        "content": p["content"],
                        "url": item["url"],
                        "src": item["src"],
                        "kws": ",".join(item["kws"][:3])
                    })
        except:
            pass

    print(f"Fetched {len(all_articles)} articles")

    uniq = []
    seen = set()
    for a in all_articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            uniq.append(a)

    print(f"Unique: {len(uniq)}")
    for a in uniq[:15]:
        print(f"  [{a['src']}] {a['title'][:60]}")

    out = f"{BRIEFING_OUTPUT_FOLDER}\\24小时国内新闻热点简报_{date_str}.docx"
    BriefingDocumentGenerator.create_word_document(
        [{"title": a["title"], "content": a["content"], "url": a["url"],
          "source_name": a["src"], "keyword": a["kws"]} for a in uniq[:50]],
        out
    )

    b = Briefing.query.get(briefing.id)
    b.docx_path = out
    for a in uniq[:50]:
        db.session.add(BriefingArticle(
            briefing_id=b.id, title=a["title"], content=a["content"],
            source_name=a["src"], source_url=a["url"],
            keyword=a["kws"], word_count=len(a["content"])
        ))
    b.article_count = len(uniq[:50])
    b.status = "completed"
    b.end_time = datetime.now()
    db.session.commit()

    print(f"Done! {len(uniq)} articles saved to {out}")
