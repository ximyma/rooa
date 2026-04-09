import warnings, sys
warnings.filterwarnings('ignore')
import logging
logging.disable(logging.WARNING)

from app import app, db
import json

with app.app_context():
    client = app.test_client()

    with app.test_request_context():
        from flask_login import login_user
        from models import User
        user = db.session.get(User, 1)
        login_user(user)

        # Test smart_search fulltext only
        print('=== smart_search fulltext ===')
        resp = client.post('/knowledge/api/smart_search',
            data=json.dumps({'query': '测试', 'kb_ids': [1], 'type': 'fulltext'}),
            content_type='application/json')
        print(f'Status: {resp.status_code}')
        if resp.status_code == 200:
            data = resp.get_json()
            print(f'Results: {len(data.get("results", []))}, Total: {data.get("total")}')

        # Test fulltext search directly
        from app import search_knowledge_fts
        result = search_knowledge_fts('测试', kb_ids=[1], user_id=1, page_size=5)
        print(f'\nsearch_knowledge_fts: {result.get("total")} results, mode={result.get("mode")}')

        # Test shared kb
        resp3 = client.get('/knowledge/shared')
        print(f'\nshared_knowledge_base: {resp3.status_code}')
