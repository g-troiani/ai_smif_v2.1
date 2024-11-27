from components.data_management_module.data_access_layer import db_manager

try:
    print("Testing database session creation...")
    session = db_manager.create_session()
    print("Database session created successfully.")
    session.close()
except Exception as e:
    print(f"Failed to create database session: {e}")
