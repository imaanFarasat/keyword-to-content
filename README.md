# Keyword Hierarchy Dashboard with Image Upload

A comprehensive web application for organizing keywords into H1, H2, H3 hierarchy and generating AI-powered content with image upload capabilities.

## Features

### Core Features
- **CSV Upload**: Upload SEMrush CSV files and organize keywords
- **Keyword Hierarchy**: Tag keywords as H1, H2, H3 with drag-and-drop reordering
- **AI Content Generation**: Generate SEO-optimized content using Gemini AI
- **Hero Section**: Manual input for hero section content (tagline, CTA, CTA link)
- **JSON Export**: Download structured JSON files for content management

### Image Upload Feature
- **Local Upload**: Upload images from your computer
- **Pexels Search**: Search and select images from Pexels
- **Custom Filenames**: Set custom filenames for each image
- **Bulk Filename**: Apply the same filename to all selected images
- **Cloudinary Integration**: Upload images to Cloudinary with custom filenames
- **URL Generation**: Get Cloudinary URLs with your custom filenames

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory with the following variables:

```env
# Gemini AI API Configuration
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Pexels API Configuration
PEXELS_API_KEY=YOUR_PEXELS_API_KEY

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=YOUR_CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY=YOUR_CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET=YOUR_CLOUDINARY_API_SECRET
```

### 3. API Keys Setup

#### Gemini AI
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

#### Pexels API
1. Go to [Pexels API](https://www.pexels.com/api/)
2. Sign up and get your API key
3. Add it to your `.env` file

#### Cloudinary
1. Go to [Cloudinary Console](https://cloudinary.com/console)
2. Sign up and get your credentials
3. Add them to your `.env` file

### 4. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## How to Use

### Basic Workflow
1. **Upload CSV**: Upload your SEMrush CSV file
2. **Organize Keywords**: Tag keywords as H1, H2, H3 and reorder them
3. **Add Hero Section**: Enter tagline, CTA text, and CTA link
4. **Upload Images** (Optional): Add images for your content
5. **Generate Content**: Let AI generate SEO-optimized content
6. **Download JSON**: Get the structured content file

### Image Upload Workflow

#### Option 1: Local Upload
1. Click "Upload from Computer"
2. Select image files from your computer
3. Customize filenames for each image
4. Use "Apply to All" to set the same filename for all images
5. Click "Upload to Cloudinary"

#### Option 2: Pexels Search
1. Click "Search Pexels"
2. Enter search terms (e.g., "nail design", "manicure")
3. Click on images to select them
4. Customize filenames
5. Click "Upload to Cloudinary"

### Filename Customization
- **Individual**: Edit filename for each image separately
- **Bulk**: Enter a filename and click "Apply to All"
- **Auto-numbering**: When using bulk filename, images are automatically numbered (e.g., `my-image-1`, `my-image-2`)

## File Structure

```
keywords-001/
├── app.py                          # Main Flask application
├── gemini_content_generator.py     # Command-line content generator
├── requirements.txt                # Python dependencies
├── env_example.txt                 # Environment variables template
├── templates/
│   └── index.html                  # Main web interface
└── uploads/                        # Temporary file storage
```

## API Endpoints

### Core Endpoints
- `POST /upload` - Upload CSV file
- `POST /filter` - Filter keywords by volume
- `POST /update_tags` - Update keyword tags
- `POST /download` - Download structured JSON
- `POST /generate_content` - Generate AI content

### Image Upload Endpoints
- `GET /search_pexels` - Search Pexels for images
- `POST /upload_to_cloudinary` - Upload local image to Cloudinary
- `POST /upload_pexels_to_cloudinary` - Upload Pexels image to Cloudinary

## JSON Output Structure

The generated JSON follows this structure:
```json
{
  "hero": {
    "tagline": "Your custom tagline",
    "cta_text": "Book Now",
    "cta_link": "book-appointment"
  },
  "head": {
    "title": "SEO-optimized title",
    "meta_description": "SEO-optimized meta description"
  },
  "body": {
    "h1_keywords": [...],
    "h2_keywords": [...],
    "faqs_html": [...]
  },
  "identifier": {
    "handle": "project-handle",
    "tags": "tag1, tag2, tag3"
  }
}
```

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all API keys are correctly set in your `.env` file
2. **Image Upload Failures**: Check Cloudinary credentials and internet connection
3. **Pexels Search Issues**: Verify Pexels API key and search terms
4. **File Permissions**: Ensure the application has write permissions for the uploads directory

### Error Messages
- "Pexels API key not configured" - Add PEXELS_API_KEY to your .env file
- "Cloudinary credentials not found" - Add Cloudinary credentials to your .env file
- "No file provided" - Select a file before uploading

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
