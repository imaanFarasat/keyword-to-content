from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import json
import os
import re
from werkzeug.utils import secure_filename
import tempfile
import google.generativeai as genai
from datetime import datetime
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Gemini AI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY environment variable not set")
    print("Please set your Gemini API key in the .env file or as an environment variable")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variable to store current data
current_data = None

def validate_handle(handle):
    """
    Validate handle format for URL usage
    Handle should be lowercase, contain only letters, numbers, and hyphens
    Multiple words should be separated by hyphens
    """
    if not handle or not isinstance(handle, str):
        return False, "Handle must be a non-empty string"
    
    # Convert to lowercase and trim whitespace
    handle = handle.strip().lower()
    
    # Check if handle is empty after trimming
    if not handle:
        return False, "Handle cannot be empty"
    
    # Check if handle contains only valid characters (letters, numbers, hyphens)
    if not re.match(r'^[a-z0-9-]+$', handle):
        return False, "Handle can only contain lowercase letters, numbers, and hyphens"
    
    # Check if handle starts or ends with hyphen
    if handle.startswith('-') or handle.endswith('-'):
        return False, "Handle cannot start or end with a hyphen"
    
    # Check if handle contains consecutive hyphens
    if '--' in handle:
        return False, "Handle cannot contain consecutive hyphens"
    
    return True, handle

def validate_tags(tags):
    """
    Validate tags format
    Tags should be comma-separated values like 'nail, nail design, manicure'
    """
    if not tags or not isinstance(tags, str):
        return False, "Tags must be a non-empty string"
    
    # Trim whitespace
    tags = tags.strip()
    
    # Check if tags is empty after trimming
    if not tags:
        return False, "Tags cannot be empty"
    
    # Split by comma and clean each tag
    tag_list = [tag.strip() for tag in tags.split(',')]
    
    # Remove empty tags
    tag_list = [tag for tag in tag_list if tag]
    
    # Check if we have any valid tags
    if not tag_list:
        return False, "At least one valid tag is required"
    
    # Check each tag for valid characters (letters, numbers, spaces)
    for tag in tag_list:
        if not re.match(r'^[a-zA-Z0-9\s]+$', tag):
            return False, f"Tag '{tag}' contains invalid characters. Only letters, numbers, and spaces are allowed"
    
    return True, ', '.join(tag_list)

def setup_gemini():
    """Setup Gemini API"""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        return model
    except Exception as e:
        print(f"❌ Error setting up Gemini AI: {e}")
        return None

def create_prompt(json_data):
    """Create a comprehensive prompt for Gemini AI"""
    prompt = f"""
You are an expert content writer and SEO specialist. You will receive a JSON structure for an article and need to fill it with high-quality, SEO-optimized content.

CURRENT JSON STRUCTURE:
{json.dumps(json_data, indent=2)}

Your tasks:

1. **Title**: Create an SEO-friendly title tag (max 60 characters) for "head.title" field
2. **Meta Description**: Create an SEO-friendly meta description (150-160 characters) for "head.meta_description" field
3. **Content**: Fill in all empty "paragraphs" arrays with 50-80 word paragraphs
4. **Bullet Points**: Fill in all empty "bullets" arrays with 3-5 relevant bullet points
5. **FAQs**: Create 15-20 FAQs in the "body.faqs_html" array, each in HTML format with:
   - Question in <h2> tags
   - Answer in <p> tags
   - You MUST generate at least 15 FAQs (20 preferred)
   - Cover a wide range of common questions about the topic

CRITICAL REQUIREMENTS:
- Keep the exact JSON structure - do not rename any keys
- Write engaging, informative content based on the topic
- Include relevant keywords naturally in the content
- Make content helpful for people interested in the topic
- Ensure all content is original and well-researched
- FAQs should cover common questions about the topic
- CRITICAL: You MUST generate at least 15 FAQs in the faqs_html array (20 preferred)

IMPORTANT: Return ONLY valid JSON. Do not include any explanations, markdown formatting, or text outside the JSON structure. The response must be parseable as valid JSON.
"""
    return prompt

def _get_faq_status(faq_count):
    """Get status message for FAQ count"""
    if faq_count >= 20:
        return f'✅ {faq_count} FAQs generated (perfect!)'
    elif faq_count >= 15:
        return f'✅ {faq_count} FAQs generated (acceptable range: 15-20)'
    else:
        return f'⚠️ Only {faq_count} FAQs generated (minimum 15 required)'

def clean_json_response(response):
    """Clean and extract JSON from AI response"""
    import re
    
    if not response or not isinstance(response, str):
        print(f"❌ Invalid response type: {type(response)}")
        return ""
    
    print(f"🔍 Cleaning response of length: {len(response)}")
    print(f"🔍 Response starts with: '{response[:100]}...'")
    
    # Try direct JSON parsing first
    try:
        json.loads(response)
        print("✅ Direct JSON parsing successful")
        return response
    except json.JSONDecodeError as e:
        print(f"⚠️ Direct JSON parsing failed: {e}")
    
    # Try to extract JSON from the response
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        extracted_json = json_match.group(0)
        print(f"🔍 Extracted JSON length: {len(extracted_json)}")
        print(f"🔍 Extracted JSON starts with: '{extracted_json[:100]}...'")
        
        # Try to fix common JSON issues
        cleaned_json = extracted_json
        
        # Fix trailing commas before closing braces and brackets
        cleaned_json = re.sub(r',(\s*[}\]])', r'\1', cleaned_json)
        
        # Fix trailing commas before closing quotes
        cleaned_json = re.sub(r',(\s*")', r'\1', cleaned_json)
        
        try:
            json.loads(cleaned_json)
            print("✅ JSON extracted and cleaned from response")
            return cleaned_json
        except json.JSONDecodeError as e:
            print(f"❌ Extracted JSON parsing failed after cleaning: {e}")
            # Try the original extracted JSON as fallback
            try:
                json.loads(extracted_json)
                print("✅ Original extracted JSON parsing successful")
                return extracted_json
            except json.JSONDecodeError:
                pass
    
    print(f"❌ No valid JSON found in response")
    return ""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return jsonify({'message': 'Flask app is working!'})

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_data
    
    print("Upload endpoint called")  # Debug print
    print(f"Request method: {request.method}")  # Debug print
    print(f"Request files: {request.files}")  # Debug print
    print(f"Request form: {request.form}")  # Debug print
    
    if 'file' not in request.files:
        print("No file in request.files")  # Debug print
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    print(f"File received: {file.filename}")  # Debug print
    print(f"File content type: {file.content_type}")  # Debug print
    
    if file.filename == '':
        print("Empty filename")  # Debug print
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.endswith('.csv'):
        try:
            # Read CSV with semicolon delimiter
            df = pd.read_csv(file, delimiter=';', encoding='utf-8')
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Convert volume to numeric, handling any non-numeric values
            df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
            
            # Remove rows with NaN volume
            df = df.dropna(subset=['Volume'])
            
            # Convert volume to integer
            df['Volume'] = df['Volume'].astype(int)
            
            # Remove exact duplicates
            df = df.drop_duplicates(subset=['Keyword'])
            
            # Convert to list of dictionaries
            keywords_data = []
            for _, row in df.iterrows():
                # Handle NaN values by converting them to None or 0
                difficulty = row.get('Keyword Difficulty', 0)
                if pd.isna(difficulty):
                    difficulty = 0
                else:
                    difficulty = float(difficulty)
                
                cpc = row.get('CPC (CAD)', 0)
                if pd.isna(cpc):
                    cpc = 0.0
                else:
                    cpc = float(cpc)
                
                intent = row.get('Intent', '')
                if pd.isna(intent):
                    intent = ''
                
                keywords_data.append({
                    'id': len(keywords_data),
                    'keyword': str(row['Keyword']),
                    'volume': int(row['Volume']),
                    'intent': str(intent),
                    'difficulty': difficulty,
                    'cpc': cpc,
                    'tag': '',  # H1, H2, H3, or empty
                    'order': len(keywords_data)
                })
            
            current_data = keywords_data
            
            return jsonify({
                'success': True,
                'message': f'Successfully loaded {len(keywords_data)} keywords',
                'data': keywords_data
            })
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")  # Debug print
            import traceback
            traceback.print_exc()  # Print full error traceback
            return jsonify({'error': f'Error processing file: {str(e)}'}), 400
    
    return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400

@app.route('/filter', methods=['POST'])
def filter_keywords():
    global current_data
    
    if current_data is None:
        return jsonify({'error': 'No data loaded'}), 400
    
    data = request.get_json()
    min_volume = data.get('min_volume', 400)
    
    try:
        min_volume = int(min_volume)
    except ValueError:
        return jsonify({'error': 'Invalid volume threshold'}), 400
    
    # Filter keywords by volume
    filtered_data = [kw for kw in current_data if kw['volume'] >= min_volume]
    
    # Update order
    for i, kw in enumerate(filtered_data):
        kw['order'] = i
    
    return jsonify({
        'success': True,
        'data': filtered_data,
        'count': len(filtered_data)
    })

@app.route('/update_tags', methods=['POST'])
def update_tags():
    global current_data
    
    if current_data is None:
        return jsonify({'error': 'No data loaded'}), 400
    
    data = request.get_json()
    updates = data.get('updates', [])
    
    for update in updates:
        keyword_id = update.get('id')
        new_tag = update.get('tag', '')
        
        # Find and update the keyword
        for kw in current_data:
            if kw['id'] == keyword_id:
                kw['tag'] = new_tag
                break
    
    return jsonify({'success': True, 'message': 'Tags updated successfully'})

@app.route('/remove_keyword', methods=['POST'])
def remove_keyword():
    global current_data
    
    if current_data is None:
        return jsonify({'error': 'No data loaded'}), 400
    
    data = request.get_json()
    keyword_id = data.get('id')
    
    # Remove the keyword
    current_data = [kw for kw in current_data if kw['id'] != keyword_id]
    
    # Update order
    for i, kw in enumerate(current_data):
        kw['order'] = i
    
    return jsonify({'success': True, 'message': 'Keyword removed successfully'})

@app.route('/reorder', methods=['POST'])
def reorder_keywords():
    global current_data
    
    if current_data is None:
        return jsonify({'error': 'No data loaded'}), 400
    
    data = request.get_json()
    new_order = data.get('order', [])
    
    # Create a mapping of id to keyword
    keyword_map = {kw['id']: kw for kw in current_data}
    
    # Reorder based on the new order
    reordered_data = []
    for i, keyword_id in enumerate(new_order):
        if keyword_id in keyword_map:
            keyword_map[keyword_id]['order'] = i
            reordered_data.append(keyword_map[keyword_id])
    
    current_data = reordered_data
    
    return jsonify({'success': True, 'message': 'Keywords reordered successfully'})

@app.route('/update_data', methods=['POST'])
def update_data():
    global current_data
    
    data = request.get_json()
    new_data = data.get('data', [])
    
    print(f"Updating backend data: {len(new_data)} keywords")  # Debug print
    
    if new_data:
        current_data = new_data
        print(f"Backend data updated successfully. Current data has {len(current_data)} keywords")  # Debug print
        return jsonify({'success': True, 'message': 'Data updated successfully'})
    else:
        print("No data provided to update")  # Debug print
        return jsonify({'error': 'No data provided'}), 400

@app.route('/download', methods=['POST'])
def download_json():
    global current_data
    
    if current_data is None:
        return jsonify({'error': 'No data loaded'}), 400
    
    # Get the latest data from the request if provided
    data = request.get_json()
    identifier = {}
    if data and 'data' in data:
        download_data = data['data']
        print(f"Using data from request: {len(download_data)} keywords")  # Debug print
        # Get identifier if provided
        identifier = data.get('identifier', {})
        # Validate identifier if it contains handle and tags
        if isinstance(identifier, dict):
            if 'handle' in identifier:
                is_valid, result = validate_handle(identifier['handle'])
                if not is_valid:
                    return jsonify({'error': f'Invalid handle: {result}'}), 400
                identifier['handle'] = result  # Use validated handle
            
            if 'tags' in identifier:
                is_valid, result = validate_tags(identifier['tags'])
                if not is_valid:
                    return jsonify({'error': f'Invalid tags: {result}'}), 400
                identifier['tags'] = result  # Use validated tags
    else:
        download_data = current_data
        print(f"Using current_data from backend: {len(download_data)} keywords")  # Debug print
    
    print(f"Downloading {len(download_data)} keywords")  # Debug print
    
    # Create filename with handle if available
    filename = 'keyword_hierarchy'
    
    # Use handle from identifier if available and valid
    if identifier and isinstance(identifier, dict) and 'handle' in identifier:
        filename = identifier['handle']
    else:
        # Fallback to H1 keyword
        h1_keywords = [kw for kw in download_data if kw['tag'] == 'H1']
        if h1_keywords:
            # Use the first H1 keyword as filename (clean it for filesystem)
            h1_keyword = h1_keywords[0]['keyword']
            # Clean filename: remove special chars, replace spaces with underscores
            clean_filename = re.sub(r'[^\w\s-]', '', h1_keyword)
            clean_filename = re.sub(r'[-\s]+', '_', clean_filename)
            filename = clean_filename.lower()
    
    # Create structured JSON data (exclude untagged keywords)
    structured_data = {
        'head': {
            'title': '',
            'meta_description': ''
        },
        'body': {
            'h1_keywords': [],
            'h2_keywords': [],
            'faqs_html': []
        }
    }
    
    # Add identifier if provided
    if identifier:
        structured_data['identifier'] = identifier
    
    # Add H1 keywords first (main topic)
    h1_keywords = [kw for kw in download_data if kw['tag'] == 'H1']
    h1_keywords.sort(key=lambda x: x['order'])
    for kw in h1_keywords:
        structured_data['body']['h1_keywords'].append({
            'keyword': str(kw['keyword'])
        })
    
    # Add H2 keywords with their related H3 keywords
    h2_keywords = [kw for kw in download_data if kw['tag'] == 'H2']
    h3_keywords = [kw for kw in download_data if kw['tag'] == 'H3']
    
    h2_keywords.sort(key=lambda x: x['order'])
    h3_keywords.sort(key=lambda x: x['order'])
    
    # Group H3 keywords under their parent H2 keywords
    for h2_kw in h2_keywords:
        h2_entry = {
            'keyword': str(h2_kw['keyword']),
            'paragraphs': [],
            'bullets': [],
            'h3_keywords': []
        }
        
        # Find H3 keywords that belong to this H2 using parent_id
        for h3_kw in h3_keywords:
            if h3_kw.get('parent_id') == h2_kw['id']:
                h2_entry['h3_keywords'].append({
                    'keyword': str(h3_kw['keyword']),
                    'paragraphs': [],
                    'bullets': []
                })
        
        structured_data['body']['h2_keywords'].append(h2_entry)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
        temp_file = f.name
    
    return send_file(
        temp_file,
        as_attachment=True,
        download_name=f'{filename}_hierarchy.json',
        mimetype='application/json'
    )

@app.route('/generate_content', methods=['POST'])
def generate_content():
    global current_data
    
    if current_data is None:
        return jsonify({'error': 'No data loaded'}), 400
    
    # Get the latest data from the request if provided
    data = request.get_json()
    print(f"🔍 Received data type: {type(data)}")
    print(f"🔍 Received data: {data}")
    
    # Get hero section data from frontend
    hero_data = data.get('hero', {}) if data else {}
    tagline = hero_data.get('tagline', '')
    cta_text = hero_data.get('cta_text', '')
    cta_link = hero_data.get('cta_link', '')
    
    if data and 'data' in data:
        json_data = data['data']
        print(f"🔍 json_data type: {type(json_data)}")
        print(f"🔍 json_data: {json_data}")
        # Get identifier if provided
        identifier = data.get('identifier', {})
        # Validate identifier if it contains handle and tags
        if isinstance(identifier, dict):
            if 'handle' in identifier:
                is_valid, result = validate_handle(identifier['handle'])
                if not is_valid:
                    return jsonify({'error': f'Invalid handle: {result}'}), 400
                identifier['handle'] = result  # Use validated handle
            
            if 'tags' in identifier:
                is_valid, result = validate_tags(identifier['tags'])
                if not is_valid:
                    return jsonify({'error': f'Invalid tags: {result}'}), 400
                identifier['tags'] = result  # Use validated tags
    else:
        json_data = current_data
        identifier = {}
    
    # Handle nested data structure
    if isinstance(json_data, dict) and 'data' in json_data:
        # Extract the actual keywords list from the nested structure
        keywords_list = json_data['data']
        # Update identifier if it's in the nested structure
        if 'identifier' in json_data:
            identifier = json_data['identifier']
            # Validate identifier if it contains handle and tags
            if isinstance(identifier, dict):
                if 'handle' in identifier:
                    is_valid, result = validate_handle(identifier['handle'])
                    if not is_valid:
                        return jsonify({'error': f'Invalid handle: {result}'}), 400
                    identifier['handle'] = result  # Use validated handle
                
                if 'tags' in identifier:
                    is_valid, result = validate_tags(identifier['tags'])
                    if not is_valid:
                        return jsonify({'error': f'Invalid tags: {result}'}), 400
                    identifier['tags'] = result  # Use validated tags
        json_data = keywords_list
        print(f"🔍 Extracted keywords list type: {type(json_data)}")
        print(f"🔍 Extracted keywords list: {json_data}")
    
    # Ensure json_data is a list
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON data: {e}")
            return jsonify({'error': f'Invalid JSON data: {str(e)}'}), 400
    
    if not isinstance(json_data, list):
        print(f"❌ Error: json_data is not a list, it's {type(json_data)}")
        return jsonify({'error': 'Data must be a list of keywords'}), 400
    
    print(f"Generating content for {len(json_data)} keywords")
    if identifier:
        print(f"🔍 Using identifier: {identifier}")
    
    # Create the structured JSON for AI processing (without hero section)
    structured_data = {
        'head': {
            'title': '',
            'meta_description': ''
        },
        'body': {
            'h1_keywords': [],
            'h2_keywords': [],
            'faqs_html': []
        }
    }
    
    # Add H1 keywords
    h1_keywords = [kw for kw in json_data if kw['tag'] == 'H1']
    h1_keywords.sort(key=lambda x: x['order'])
    for kw in h1_keywords:
        structured_data['body']['h1_keywords'].append({
            'keyword': str(kw['keyword'])
        })
    
    # Add H2 keywords with their related H3 keywords
    h2_keywords = [kw for kw in json_data if kw['tag'] == 'H2']
    h3_keywords = [kw for kw in json_data if kw['tag'] == 'H3']
    
    h2_keywords.sort(key=lambda x: x['order'])
    h3_keywords.sort(key=lambda x: x['order'])
    
    for h2_kw in h2_keywords:
        h2_entry = {
            'keyword': str(h2_kw['keyword']),
            'paragraphs': [],
            'bullets': [],
            'h3_keywords': []
        }
        
        # Find H3 keywords that belong to this H2 using parent_id
        for h3_kw in h3_keywords:
            if h3_kw.get('parent_id') == h2_kw['id']:
                h2_entry['h3_keywords'].append({
                    'keyword': str(h3_kw['keyword']),
                    'paragraphs': [],
                    'bullets': []
                })
        
        structured_data['body']['h2_keywords'].append(h2_entry)
    
    try:
        # Setup Gemini
        model = setup_gemini()
        if not model:
            return jsonify({'error': 'Failed to setup Gemini AI'}), 500
        
        # Create prompt
        prompt = create_prompt(structured_data)
        
        # Send to Gemini
        print("🔄 Sending request to Gemini AI...")
        start_time = time.time()
        try:
            response = model.generate_content(prompt)
            processing_time = time.time() - start_time
            print(f"✅ Gemini API call completed in {processing_time:.1f}s")
        except Exception as e:
            print(f"❌ Error calling Gemini API: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Failed to call Gemini API: {str(e)}'}), 500
        
        print(f"🔍 Raw response from Gemini: {response}")
        print(f"🔍 Response type: {type(response)}")
        print(f"🔍 Response text: {response.text if hasattr(response, 'text') else 'No text attribute'}")
        
        if response and hasattr(response, 'text') and response.text and response.text.strip():
            print(f"🔍 Response text length: {len(response.text)}")
            print(f"🔍 Response text preview: {response.text[:200]}...")
            
            # Clean the response
            cleaned_result = clean_json_response(response.text)
            print(f"🔍 Cleaned result length: {len(cleaned_result) if cleaned_result else 0}")
            print(f"🔍 Cleaned result: '{cleaned_result}'")
            
            if not cleaned_result or not cleaned_result.strip():
                print("❌ Error: Cleaned result is empty")
                print(f"🔍 Original response text: '{response.text}'")
                return jsonify({'error': 'AI returned empty response'}), 500
            
            # Try to parse as JSON
            try:
                ai_generated_data = json.loads(cleaned_result)
                print(f"✅ JSON parsed successfully, data keys: {list(ai_generated_data.keys())}")
            except json.JSONDecodeError as e:
                print(f"❌ Error: Response is not valid JSON: {e}")
                print(f"❌ Failed to parse: {cleaned_result}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': 'AI response is not valid JSON'}), 500
            
            # Validate FAQ count
            faqs_count = len(ai_generated_data.get('body', {}).get('faqs_html', []))
            if faqs_count < 15:
                print(f"⚠️ Warning: Generated {faqs_count} FAQs (minimum 15 required). Regenerating...")
                # Try to regenerate with a more explicit prompt
                enhanced_prompt = prompt + "\n\nCRITICAL REMINDER: You MUST generate AT LEAST 15 FAQs in the faqs_html array. Current count: " + str(faqs_count) + ". Please regenerate with at least 15 FAQs (20 preferred)."
                try:
                    response = model.generate_content(enhanced_prompt)
                    if response and hasattr(response, 'text') and response.text:
                        cleaned_result = clean_json_response(response.text)
                        try:
                            ai_generated_data = json.loads(cleaned_result)
                            faqs_count = len(ai_generated_data.get('body', {}).get('faqs_html', []))
                            print(f"✅ Regenerated with {faqs_count} FAQs")
                        except json.JSONDecodeError:
                            print("⚠️ Regeneration failed, using original result")
                except Exception as e:
                    print(f"⚠️ Regeneration failed: {e}, using original result")
            elif faqs_count < 20:
                print(f"✅ Generated {faqs_count} FAQs (acceptable range: 15-20)")
            else:
                print(f"✅ Generated {faqs_count} FAQs (perfect!)")
            
            # Add identifier to the final output if provided
            if identifier:
                ai_generated_data['identifier'] = identifier
            
            # Add hero section manually (not generated by AI)
            ai_generated_data['hero'] = {
                'tagline': tagline,
                'cta_text': cta_text,
                'cta_link': cta_link
            }
            
            # Reorder keys to match required structure: hero, head, body, identifier
            ordered_data = {}
            if 'hero' in ai_generated_data:
                ordered_data['hero'] = ai_generated_data['hero']
            if 'head' in ai_generated_data:
                ordered_data['head'] = ai_generated_data['head']
            if 'body' in ai_generated_data:
                ordered_data['body'] = ai_generated_data['body']
            if 'identifier' in ai_generated_data:
                ordered_data['identifier'] = ai_generated_data['identifier']
            
            # Create output filename with handle
            h1_keywords = [kw for kw in json_data if kw['tag'] == 'H1']
            filename = 'keyword_content'
            
            # Use handle from identifier if available and valid
            handle_part = ''
            if identifier and isinstance(identifier, dict) and 'handle' in identifier:
                handle = identifier['handle']
                is_valid, result = validate_handle(handle)
                if is_valid:
                    handle_part = f"{result}_"
                else:
                    print(f"⚠️ Warning: Invalid handle '{handle}': {result}")
            
            # Fallback to H1 keyword if no valid handle
            if not handle_part and h1_keywords:
                h1_keyword = h1_keywords[0]['keyword']
                clean_filename = re.sub(r'[^\w\s-]', '', h1_keyword)
                clean_filename = re.sub(r'[-\s]+', '_', clean_filename)
                filename = clean_filename.lower()
            elif handle_part:
                filename = handle_part.rstrip('_')  # Remove trailing underscore
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f'{filename}_filled_{timestamp}.json'
            
            # Create the target directory if it doesn't exist
            target_dir = 'D:/articles/nails'
            os.makedirs(target_dir, exist_ok=True)
            
            # Full path for the output file
            output_path = os.path.join(target_dir, output_filename)
            
            # Save the result to the target directory
            try:
                with open(output_path, 'w', encoding='utf-8') as file:
                    json.dump(ordered_data, file, indent=2, ensure_ascii=False)
                
                print(f"✅ Content generated and saved to: {output_path}")
                
                # Create response data
                response_data = {
                    'success': True,
                    'message': f'Content generated successfully in {processing_time:.1f}s',
                    'filename': output_filename,
                    'file_path': output_path,
                    'summary': {
                        'title': ordered_data.get('head', {}).get('title', 'Not provided'),
                        'meta_description': ordered_data.get('head', {}).get('meta_description', 'Not provided'),
                        'hero_tagline': ordered_data.get('hero', {}).get('tagline', 'Not provided'),
                        'hero_cta': ordered_data.get('hero', {}).get('cta_text', 'Not provided'),
                        'hero_cta_link': ordered_data.get('hero', {}).get('cta_link', 'Not provided'),
                        'h2_sections': len(ordered_data.get('body', {}).get('h2_keywords', [])),
                        'faqs_generated': len(ordered_data.get('body', {}).get('faqs_html', [])),
                        'faqs_status': _get_faq_status(len(ordered_data.get('body', {}).get('faqs_html', [])))
                    }
                }
                
                print(f"✅ Response data prepared: {response_data}")
                return jsonify(response_data)
                
            except Exception as file_error:
                print(f"❌ Error saving file or creating response: {file_error}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Error saving file: {str(file_error)}'}), 500
        else:
            print("❌ Error: No valid response from Gemini AI")
            if response:
                print(f"❌ Response object: {response}")
                if hasattr(response, 'text'):
                    print(f"❌ Response text: '{response.text}'")
            return jsonify({'error': 'No valid response from Gemini AI'}), 500
            
    except Exception as e:
        print(f"❌ Error generating content: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error generating content: {str(e)}'}), 500

@app.route('/download_generated/<filename>')
def download_generated_file(filename):
    """Serve generated JSON files for download"""
    try:
        # Check if file exists and is a JSON file
        target_dir = 'D:/articles/nails'
        file_path = os.path.join(target_dir, filename)
        
        if not filename.endswith('.json') or not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        print(f"✅ Serving file for download: {file_path}")
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    except Exception as e:
        print(f"❌ Error serving file {filename}: {e}")
        return jsonify({'error': 'Error serving file'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
