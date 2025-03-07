import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from werkzeug.utils import secure_filename
import uuid

# Configure Cloudinary
def configure_cloudinary():
    """Setup Cloudinary with environment variables"""
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET')
    )

def upload_to_cloudinary(file):
    """Upload a file to Cloudinary and return the result"""
    if not file:
        return None
        
    # Generate unique filename
    original_filename = secure_filename(file.filename)
    unique_id = f"dsa_flashcard_{uuid.uuid4().hex}"
    
    # Upload to cloudinary
    result = cloudinary.uploader.upload(
        file,
        public_id=unique_id,
        folder="dsa_flashcards",
        resource_type="auto"
    )
    
    return {
        'public_id': result['public_id'],
        'url': result['secure_url'],
        'original_filename': original_filename
    }
    
def delete_from_cloudinary(public_id):
    """Delete an image from Cloudinary by public ID"""
    if not public_id:
        return None
    
    return cloudinary.uploader.destroy(public_id)
    
def get_cloudinary_url(public_id, **options):
    """Get a Cloudinary URL with optional transformations"""
    if not public_id:
        return None
        
    return cloudinary.CloudinaryImage(public_id).build_url(**options)
