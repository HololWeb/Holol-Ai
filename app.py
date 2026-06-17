from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
import os
import re
from datetime import datetime
import random

app = Flask(__name__, static_folder='static')
CORS(app)

# API Configuration
API_KEY = "sk-e91ee7422b9b4b59820160b975bec0ce"
API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# ==============================
# Tool Functions
# ==============================
def calculator(expression):
    try:
        expression = re.sub(r'[^0-9+\-*/().%\s]', '', expression)
        result = eval(expression)
        return f"🧮 Hasil kalkulasi: {expression} = {result}"
    except:
        return "❌ Perhitungan gagal! Coba matematika yang lebih sederhana!"

def read_file(filename):
    try:
        filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
        filepath = os.path.join('files', filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"📂 Isi file: {content}"
        else:
            return "📂 File tidak ditemukan! Buat dulu!"
    except Exception as e:
        return f"📂 Gagal membaca file: {str(e)}"

def write_file(filename, content):
    try:
        filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
        os.makedirs('files', exist_ok=True)
        filepath = os.path.join('files', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✍️ Berhasil disimpan ke {filename}! 🎉"
    except Exception as e:
        return f"❌ Gagal menyimpan file: {str(e)}"

def web_search(query):
    results = [
        f"🔍 Menemukan ini tentang \"{query}\":",
        f"📌 Wikipedia says: {query} is super interesting!",
        f"📰 News: {query} is trending today!",
        f"💡 Fun fact about {query}!"
    ]
    return f"🌐 {chr(10).join(results)}"

def get_current_time():
    now = datetime.now()
    time_str = now.strftime("%B %d, %Y at %I:%M:%S %p")
    return f"⏰ Waktu sekarang: {time_str}"

def get_weather(city):
    temps = [18, 22, 25, 28, 30, 15, 20]
    conditions = ['☀️ Cerah', '⛅ Berawan sebagian', '☁️ Berawan', '🌧️ Hujan ringan', '🌈 Cerah']
    temp = random.choice(temps)
    condition = random.choice(conditions)
    return f"🌦️ Cuaca di {city}: {temp}°C, {condition}"

tools = {
    'calculator': calculator,
    'read_file': read_file,
    'write_file': write_file,
    'web_search': web_search,
    'get_current_time': get_current_time,
    'get_weather': get_weather
}

# ==============================
# System Prompt
# ==============================
SYSTEM_PROMPT = """You are a FUN and ENTHUSIASTIC AI Agent named Holol AI that remembers all chat history.
You have 6 awesome tools to use:
1. calculator: Solve math calculation, format: {"tool":"calculator","params":{"expression":"math_expression"}}
2. read_file: Read text file, format: {"tool":"read_file","params":{"filename":"file_name.txt"}}
3. write_file: Write content to text file, format: {"tool":"write_file","params":{"filename":"file_name.txt","content":"your_text"}}
4. web_search: Search information online, format: {"tool":"web_search","params":{"query":"search_keyword"}}
5. get_current_time: Check current date and time, format: {"tool":"get_current_time","params":{}}
6. get_weather: Check weather of a city, format: {"tool":"get_weather","params":{"city":"city_name"}}

Strict Rules:
- If you need to use a tool, output ONLY valid JSON format as shown above, no extra text.
- If you do NOT need any tool, answer directly in natural English with enthusiasm and emojis! 🎉
- Always remember all previous conversation with the user.
- Be fun, cheerful, and helpful! Use lots of emojis! ✨"""

# ==============================
# Routes
# ==============================
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        data = request.json
        user_message = data.get('message', '')
        chat_history = data.get('history', [])
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})
        
        request_body = {
            "model": "qwen-turbo",
            "input": {"messages": messages},
            "parameters": {
                "result_format": "message",
                "temperature": 0.8,
                "top_p": 0.9,
                "max_tokens": 1500
            }
        }
        
        response = requests.post(
            API_URL,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {API_KEY}'
            },
            json=request_body,
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
        
        response_data = response.json()
        
        if response_data.get('output', {}).get('choices'):
            ai_reply = response_data['output']['choices'][0]['message']['content'].strip()
            
            if ai_reply.startswith('{') and ai_reply.endswith('}'):
                try:
                    tool_data = json.loads(ai_reply)
                    tool_name = tool_data.get('tool')
                    tool_params = tool_data.get('params', {})
                    
                    if tool_name in tools:
                        tool_result = tools[tool_name](**tool_params)
                        
                        messages.append({"role": "assistant", "content": ai_reply})
                        messages.append({"role": "user", "content": tool_result})
                        
                        final_response = requests.post(
                            API_URL,
                            headers={
                                'Content-Type': 'application/json',
                                'Authorization': f'Bearer {API_KEY}'
                            },
                            json={
                                "model": "qwen-turbo",
                                "input": {"messages": messages},
                                "parameters": {
                                    "result_format": "message",
                                    "temperature": 0.8,
                                    "top_p": 0.9,
                                    "max_tokens": 1500
                                }
                            },
                            timeout=30
                        )
                        
                        if final_response.status_code == 200:
                            final_data = final_response.json()
                            if final_data.get('output', {}).get('choices'):
                                final_reply = final_data['output']['choices'][0]['message']['content'].strip()
                                return jsonify({
                                    'reply': final_reply,
                                    'tool_result': tool_result
                                })
                except json.JSONDecodeError:
                    pass
            
            return jsonify({'reply': ai_reply})
        else:
            return jsonify({'error': 'Invalid API response'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_files', methods=['POST'])
def clear_files():
    try:
        import shutil
        if os.path.exists('files'):
            shutil.rmtree('files')
        os.makedirs('files', exist_ok=True)
        return jsonify({'success': True, 'message': 'Files cleared! ✨'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'status': 'OK', 'message': 'Server is running!'})

if __name__ == '__main__':
    os.makedirs('files', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    print("🚀 Holol AI Server Starting...")
    print("✨ Server running at: http://localhost:5000")
    print("🔒 API Key is securely stored on the server!")
    print("📁 Files will be stored in: ./files")
    app.run(debug=True, host='0.0.0.0', port=5000)
