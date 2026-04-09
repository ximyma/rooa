from app import app, db
from sqlalchemy import text

app.config['TESTING'] = True

with app.app_context():
    # Check if column exists
    result = db.session.execute(text("PRAGMA table_info(archive_files)"))
    columns = [row[1] for row in result]
    print('Current columns:', columns)
    
    if 'full_archive_code' not in columns:
        print('Adding full_archive_code column...')
        try:
            db.session.execute(text("ALTER TABLE archive_files ADD COLUMN full_archive_code VARCHAR(100)"))
            db.session.commit()
            print('Column added successfully!')
        except Exception as e:
            print(f'Error adding column: {e}')
            db.session.rollback()
    else:
        print('Column already exists')
    
    # Also check for other potentially missing columns
    # Let me check what columns are expected by the model
    from archive_models import ArchiveFile
    import inspect
    
    model_columns = [c.name for c in ArchiveFile.__table__.columns]
    print('\nModel expected columns:', model_columns)
    
    missing = set(model_columns) - set(columns)
    if missing:
        print(f'\nMissing columns: {missing}')
        for col in missing:
            print(f'Adding column: {col}')
            # Get column type from model
            col_obj = ArchiveFile.__table__.columns[col]
            col_type = str(col_obj.type)
            try:
                # Simple approach - just add VARCHAR
                db.session.execute(text(f"ALTER TABLE archive_files ADD COLUMN {col} VARCHAR(500)"))
                db.session.commit()
                print(f'  Added: {col}')
            except Exception as e:
                print(f'  Error adding {col}: {e}')
                db.session.rollback()
