from app import app, db

app.config['TESTING'] = True

with app.app_context():
    try:
        from archive_models import ArchiveFonds, ArchiveCatalog, ArchiveVolume, ArchiveFile, ArchiveBorrow
        print('Models imported OK')
        
        # Check table existence
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print('Tables:', tables)
        
        # Check if archive tables exist
        archive_tables = [t for t in tables if 'archive' in t.lower()]
        print('Archive tables:', archive_tables)
        
        # Try to count records
        if 'archive_fonds' in tables:
            count = ArchiveFonds.query.count()
            print(f'ArchiveFonds count: {count}')
        else:
            print('ArchiveFonds table does not exist')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
