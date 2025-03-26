from flask import Flask, request, jsonify
from flask_cors import CORS
from together import Together
import os

app = Flask(__name__)
CORS(app)

# Retrieve API key from environment variable
TOGETHER_API_KEY = os.environ.get('TOGETHER_API_KEY')

@app.route('/generate-code', methods=['POST', 'OPTIONS'])
def generate_code():
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        response = jsonify(success=True)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    # Get the request data
    data = request.json

    language = data.get('language', 'js')
    html_code = data.get('htmlCode', '')
    css_code = data.get('cssCode', '')
    js_code = data.get('jsCode', '')
    user_prompt = data.get('prompt', 'Enhance this code with best practices and optimizations')

    # Initialize the Together API client
    client = Together(api_key=TOGETHER_API_KEY)

    # Create the prompt based on the language
    system_prompt = "You are a helpful coding assistant that provides enhanced code."

    prompt_content = f"""Enhance this {language.upper()} code. No external images and no external links.
    Everything should be in one worker code. Create your own SVGs and provide the full code.

    Current HTML: {html_code}
    Current CSS: {css_code}
    Current JS: {js_code}

    User instructions: {user_prompt}

    Please improve the {language.upper()} code specifically.
    Only return the improved code without explanations or markdown formatting.
    """

    # Call the Together API
    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt_content
            }
        ],
        max_tokens=5576,
        temperature=0.7,
        top_p=0.7,
        top_k=50,
        repetition_penalty=1,
        stop=["<｜end▁of▁sentence｜>"],
        stream=True
    )

    # Process the response
    collected_output = ""
    code_content = ""
    is_inside_code_block = False

    for chunk in response:
        if hasattr(chunk, 'choices') and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            collected_output += content

            # Check for code block markers
            if '```' in content:
                parts = content.split('```')
                for i in range(len(parts)):
                    if i % 2 == 1:  # Inside code block
                        code_content += parts[i].strip(language + '\n')
                    elif is_inside_code_block:  # End of a code block
                        code_content += parts[i]
                        is_inside_code_block = False
            elif is_inside_code_block:
                code_content += content

    # Extract code if the model returned it with markdown formatting
    if '```' in collected_output:
        # Try to extract code between code blocks
        code_blocks = collected_output.split('```')
        for i in range(1, len(code_blocks), 2):
            block = code_blocks[i]
            if block.startswith(language) or block.startswith(language.lower()):
                code_content = block.replace(language, '', 1).replace(language.lower(), '', 1).strip()
                break
        if not code_content:
            code_content = collected_output
    else:
        # No code blocks, just return the entire output
        code_content = collected_output

    # Return the collected output with CORS headers
    response = jsonify({
        'generatedCode': code_content,
        'language': language
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/analyze-text', methods=['POST', 'OPTIONS'])
def analyze_text():
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        response = jsonify(success=True)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    # Get the user prompt
    data = request.json
    user_prompt = data.get('prompt', 'Analyze this code and provide recommendations')

    # Add a system prompt to guide the analysis
    system_prompt = "You are a helpful code analysis assistant. Provide me meaning other such examples."

    try:
        # Initialize the Together API client
        client = Together(api_key=TOGETHER_API_KEY)

        # Call the Together API
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt  # Use the actual user prompt
                }
            ],
            max_tokens=4096,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<｜end▁of▁sentence｜>"],
            stream=False
        )

        # Extract analysis from the response
        analysis = response.choices[0].message.content if response.choices else "No analysis available"

        # Return the analysis with CORS headers
        response = jsonify({
            'analysis': analysis
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        # Return error with CORS headers
        response = jsonify({
            'error': 'Analysis failed', 
            'details': str(e)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/ping', methods=['GET'])
def ping():
    response = jsonify({"status": "ok", "message": "Server is running"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# This is required for Vercel
def handler(event, context):
    return app(event, context)
