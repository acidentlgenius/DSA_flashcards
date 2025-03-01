import os

# Create uploads directory for image storage
uploads_dir = os.path.join('static', 'uploads')
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
    print(f"Created directory: {uploads_dir}")
else:
    print(f"Directory already exists: {uploads_dir}")
