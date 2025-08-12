from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import json
import os
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
GEMINI_API_KEY = "AIzaSyCnHLY38mv1nvmYV-2OXRacLXKjs5wItXQ"
genai.configure(api_key=GEMINI_API_KEY)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variable to store current data
current_data = None

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
5. **FAQs**: Create exactly 4 FAQs in the "body.faqs_html" array, each in HTML format with:
   - Question in <h2> tags
   - Answer in <p> tags

CRITICAL REQUIREMENTS:
- Keep the exact JSON structure - do not rename any keys
- Write engaging, informative content based on the topic
- Include relevant keywords naturally in the content
- Make content helpful for people interested in the topic
- Ensure all content is original and well-researched
- FAQs should cover common questions about the topic

IMPORTANT: Return ONLY valid JSON. Do not include any explanations, markdown formatting, or text outside the JSON structure. The response must be parseable as valid JSON.
"""
    return prompt

def clean_json_response(response):
    """Clean and extract JSON from AI response"""
    import re
    
    # Try direct JSON parsing first
    try:
        json.loads(response)
        return response
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from the response
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        extracted_json = json_match.group(0)
        try:
            json.loads(extracted_json)
            print("✅ JSON extracted from response")
            return extracted_json
        except json.JSONDecodeError:
            pass
    
    return response

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
    if data and 'data' in data:
        download_data = data['data']
        print(f"Using data from request: {len(download_data)} keywords")  # Debug print
    else:
        download_data = current_data
        print(f"Using current_data from backend: {len(download_data)} keywords")  # Debug print
    
    print(f"Downloading {len(download_data)} keywords")  # Debug print
    
    # Get H1 keyword for filename
    h1_keywords = [kw for kw in download_data if kw['tag'] == 'H1']
    filename = 'keyword_hierarchy'
    if h1_keywords:
        # Use the first H1 keyword as filename (clean it for filesystem)
        h1_keyword = h1_keywords[0]['keyword']
        # Clean filename: remove special chars, replace spaces with underscores
        import re
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
    if data and 'data' in data:
        json_data = data['data']
    else:
        json_data = current_data
    
    print(f"Generating content for {len(json_data)} keywords")
    
    # Create the structured JSON for AI processing
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
        response = model.generate_content(prompt)
        processing_time = time.time() - start_time
        
        if response and response.text:
            # Clean the response
            cleaned_result = clean_json_response(response.text)
            
            # Try to parse as JSON
            try:
                ai_generated_data = json.loads(cleaned_result)
            except json.JSONDecodeError as e:
                print(f"❌ Error: Response is not valid JSON: {e}")
                return jsonify({'error': 'AI response is not valid JSON'}), 500
            
            # Create output filename
            h1_keywords = [kw for kw in json_data if kw['tag'] == 'H1']
            filename = 'keyword_content'
            if h1_keywords:
                h1_keyword = h1_keywords[0]['keyword']
                import re
                clean_filename = re.sub(r'[^\w\s-]', '', h1_keyword)
                clean_filename = re.sub(r'[-\s]+', '_', clean_filename)
                filename = clean_filename.lower()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f'{filename}_filled_{timestamp}.json'
            
            # Save the result
            with open(output_filename, 'w', encoding='utf-8') as file:
                json.dump(ai_generated_data, file, indent=2, ensure_ascii=False)
            
            print(f"✅ Content generated and saved to: {output_filename}")
            
            return jsonify({
                'success': True,
                'message': f'Content generated successfully in {processing_time:.1f}s',
                'filename': output_filename,
                'summary': {
                    'title': ai_generated_data.get('head', {}).get('title', 'Not provided'),
                    'meta_description': ai_generated_data.get('head', {}).get('meta_description', 'Not provided'),
                    'h2_sections': len(ai_generated_data.get('body', {}).get('h2_keywords', [])),
                    'faqs_generated': len(ai_generated_data.get('body', {}).get('faqs_html', []))
                }
            })
        else:
            return jsonify({'error': 'No response from Gemini AI'}), 500
            
    except Exception as e:
        print(f"❌ Error generating content: {e}")
        return jsonify({'error': f'Error generating content: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
