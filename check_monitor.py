"""Check monitor library data"""
from app import app, db
from models import UrlLibrary, MonitorResult

with app.app_context():
    libraries = UrlLibrary.query.all()
    print('UrlLibraries:')
    for lib in libraries:
        print(f'  ID={lib.id}, Name={lib.name}')
        results = MonitorResult.query.filter_by(library_id=lib.id).count()
        print(f'    Results count: {results}')

    print('\nTotal libraries:', len(libraries))
