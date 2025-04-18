from app import app, db

with app.app_context():
    try:
        tables = db.metadata.tables.keys()
        print("Tables in database:")
        for table in tables:
            print(f"- {table}")
        if not tables:
            print("No tables found.")
    except Exception as e:
        print(f"Error accessing database: {e}")