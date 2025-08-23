import json
import google.generativeai as genai
import os
from typing import Dict, Any
from datetime import datetime
import time

# Configure Gemini API
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

def setup_gemini():
    """Setup Gemini API"""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        return model
    except Exception as e:
        print(f"❌ Error setting up Gemini AI: {e}")
        return None

def load_json_data(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"❌ Error: {file_path} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {file_path}: {e}")
        return None

def create_prompt(json_data: Dict[str, Any]) -> str:
    """Create a comprehensive prompt for Gemini AI"""
    
    prompt = f"""
You are an expert content writer and SEO specialist. You will receive a JSON structure for an article and need to fill it with high-quality, SEO-optimized content.

CURRENT JSON STRUCTURE:
{json.dumps(json_data, indent=2)}

Your tasks:

1. **Title**: Create an SEO-friendly title tag (max 60 characters) for "title" field
2. **Meta Description**: Create an SEO-friendly meta description (150-160 characters) for "meta_description" field
3. **Content**: Fill in all empty "paragraphs" arrays with 50-80 word paragraphs
4. **Bullet Points**: Fill in all empty "bullets" arrays with 3-5 relevant bullet points
5. **FAQs**: Create EXACTLY 20 FAQs in the "faqs_html" array, each in HTML format with:
   - Question in <h2> tags
   - Answer in <p> tags
   - You MUST generate exactly 20 FAQs - no more, no less
   - Cover a wide range of common questions about the topic

CRITICAL REQUIREMENTS:
- Keep the exact JSON structure - do not rename any keys
- Write engaging, informative content based on the topic
- Include relevant keywords naturally in the content
- Make content helpful for people interested in the topic
- Ensure all content is original and well-researched
- FAQs should cover common questions about the topic
- CRITICAL: You MUST generate exactly 20 FAQs in the faqs_html array - this is non-negotiable
- DO NOT add a hero section - it will be added manually

IMPORTANT: Return ONLY valid JSON. Do not include any explanations, markdown formatting, or text outside the JSON structure. The response must be parseable as valid JSON.
"""
    return prompt

def send_to_gemini(model, prompt: str) -> str:
    """Send prompt to Gemini AI and get response"""
    try:
        print("🔄 Sending request to Gemini AI...")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Error communicating with Gemini AI: {e}")
        return None

def clean_json_response(response: str) -> str:
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
        
        # Try to fix common JSON issues
        cleaned_json = extracted_json
        
        # Fix trailing commas before closing braces and brackets
        cleaned_json = re.sub(r',(\s*[}\]])', r'\1', cleaned_json)
        
        # Fix trailing commas before closing quotes
        cleaned_json = re.sub(r',(\s*")', r'\1', cleaned_json)
        
        # Fix trailing commas in object properties
        cleaned_json = re.sub(r',(\s*})', r'\1', cleaned_json)
        
        # Fix trailing commas in arrays
        cleaned_json = re.sub(r',(\s*\])', r'\1', cleaned_json)
        
        # Remove any stray characters at the end
        cleaned_json = re.sub(r'[^\w\s\{\}\[\]",:.\-_\s]+$', '', cleaned_json)
        
        # Remove any trailing single quotes
        cleaned_json = re.sub(r"'$", '', cleaned_json)
        
        try:
            json.loads(cleaned_json)
            print("✅ JSON extracted and cleaned from response")
            return cleaned_json
        except json.JSONDecodeError:
            try:
                json.loads(extracted_json)
                print("✅ JSON extracted from response")
                return extracted_json
            except json.JSONDecodeError:
                pass
    
    return response

def validate_and_fix_json(json_data):
    """Validate and fix JSON data before saving"""
    import re
    
    if isinstance(json_data, str):
        # If it's a string, try to parse it first
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            print(f"❌ JSON validation failed: {e}")
            return None
    
    # Convert back to string for cleaning
    json_string = json.dumps(json_data, indent=2, ensure_ascii=False)
    
    # Apply comprehensive cleaning
    cleaned_json = json_string
    
    # Fix trailing commas in objects
    cleaned_json = re.sub(r',(\s*})', r'\1', cleaned_json)
    
    # Fix trailing commas in arrays
    cleaned_json = re.sub(r',(\s*\])', r'\1', cleaned_json)
    
    # Remove any stray characters at the end
    cleaned_json = re.sub(r'[^\w\s\{\}\[\]",:.\-_\s]+$', '', cleaned_json)
    
    # Remove any trailing single quotes
    cleaned_json = re.sub(r"'$", '', cleaned_json)
    
    # Try to parse the cleaned JSON
    try:
        validated_data = json.loads(cleaned_json)
        print("✅ JSON validated and cleaned successfully")
        return validated_data
    except json.JSONDecodeError as e:
        print(f"❌ JSON validation failed after cleaning: {e}")
        return None

def save_result(result: str, original_file: str) -> bool:
    """Save the filled JSON result to a file"""
    try:
        # Clean the response
        cleaned_result = clean_json_response(result)
        
        # Try to parse as JSON
        try:
            json_data = json.loads(cleaned_result)
            
            # Validate and fix JSON before saving
            validated_data = validate_and_fix_json(json_data)
            if validated_data is None:
                print(f"❌ Error: Failed to validate JSON data")
                print("\n📄 Raw AI Response:")
                print("-" * 50)
                print(cleaned_result)
                print("-" * 50)
                return False
            
            json_data = validated_data
            
            # Validate FAQ count
            faqs_count = len(json_data.get('faqs_html', []))
            if faqs_count != 20:
                print(f"⚠️ Warning: Generated {faqs_count} FAQs instead of 20.")
                print("⚠️ Please regenerate content to get exactly 20 FAQs.")
                    
        except json.JSONDecodeError as e:
            print(f"❌ Error: Response is not valid JSON: {e}")
            print("\n📄 Raw AI Response:")
            print("-" * 50)
            print(cleaned_result)
            print("-" * 50)
            return False
        
        # Create output filename
        base_name = os.path.splitext(original_file)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{base_name}_filled_{timestamp}.json"
        
        # Save the result
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(json_data, file, indent=2, ensure_ascii=False)
        
        print(f"✅ Result saved to: {output_file}")
        
        # Show summary
        print("\n📊 Generated Content Summary:")
        print(f"   Title: {json_data.get('title', 'Not provided')}")
        print(f"   Meta Description: {json_data.get('meta_description', 'Not provided')}")
        print(f"   H2 Sections: {len(json_data.get('h2_keywords', []))}")
        faqs_count = len(json_data.get('faqs_html', []))
        print(f"   FAQs Generated: {faqs_count}")
        if faqs_count == 20:
            print("   ✅ FAQ Status: Exactly 20 FAQs generated")
        else:
            print(f"   ⚠️ FAQ Status: Only {faqs_count} FAQs generated (should be 20)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving result: {e}")
        return False

def main():
    """Main function to orchestrate the process"""
    print("🤖 Enhanced Gemini AI Content Generator")
    print("=" * 50)
    
    # Get input file
    input_file = input("📁 Enter JSON file path (or press Enter for 'Acrylic Nails.json'): ").strip()
    if not input_file:
        input_file = "Acrylic Nails.json"
    
    print(f"📂 Processing: {input_file}")
    
    # Load JSON data
    json_data = load_json_data(input_file)
    if not json_data:
        return
    
    print("✅ JSON file loaded successfully")
    
    # Setup Gemini
    model = setup_gemini()
    if not model:
        return
    
    print("✅ Gemini AI configured successfully")
    
    # Create prompt
    prompt = create_prompt(json_data)
    print("✅ Prompt created")
    
    # Send to Gemini
    start_time = time.time()
    result = send_to_gemini(model, prompt)
    
    if result:
        processing_time = time.time() - start_time
        print(f"✅ Received response from Gemini AI ({processing_time:.1f}s)")
        
        # Save result
        if save_result(result, input_file):
            print("\n🎉 Process completed successfully!")
        else:
            print("\n⚠️ Process completed but there was an issue with the response format.")
    else:
        print("❌ Failed to get response from Gemini AI")

if __name__ == "__main__":
    main()
