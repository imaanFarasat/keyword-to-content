# Security Setup Guide

## ⚠️ IMPORTANT: API Key Security

Your Google Gemini API key has been exposed in the repository. Follow these steps immediately:

### 1. Revoke the Exposed API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Find the exposed API key: `AIzaSyCnHLY38mv1nvmYV-2OXRacLXKjs5wItXQ`
3. Click the trash icon to delete/revoke it
4. Create a new API key

### 2. Set Up Environment Variables

#### Option A: Using .env file (Recommended for development)
1. Copy `env_example.txt` to `.env`
2. Replace `YOUR_NEW_API_KEY_HERE` with your new API key:
   ```
   GEMINI_API_KEY=your_new_api_key_here
   ```

#### Option B: Using system environment variables
Set the environment variable in your system:
- **Windows**: `set GEMINI_API_KEY=your_new_api_key_here`
- **Linux/Mac**: `export GEMINI_API_KEY=your_new_api_key_here`

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Setup
Run the application to ensure it works with the new API key:
```bash
python app.py
```

## Security Best Practices

1. **Never commit API keys to version control**
2. **Use environment variables for all sensitive data**
3. **Keep your .env file in .gitignore**
4. **Regularly rotate your API keys**
5. **Monitor your API usage for unusual activity**

## Files Updated for Security

- ✅ `app.py` - Now uses environment variables only
- ✅ `gemini_content_generator.py` - Now uses environment variables only
- ✅ `requirements.txt` - Added python-dotenv dependency
- ✅ `.gitignore` - Prevents .env files from being committed
- ✅ `env_example.txt` - Template for environment setup

## Next Steps

1. **Immediately revoke the old API key**
2. **Create a new API key**
3. **Set up your .env file**
4. **Test the application**
5. **Consider using a secrets management service for production**
