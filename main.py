import os
import base64
import io
from flask import Flask, request, jsonify
from PIL import Image
import rembg

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CORS HEADERS - Permite que fetch() desde navegadores (iPhone Safari) funcione
# ═══════════════════════════════════════════════════════════════════════════
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.options('/remove-bg')
def options_remove_bg():
    return '', 200

@app.options('/remove-bg-url')
def options_remove_bg_url():
    return '', 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    """
    POST /remove-bg
    Body: JSON with 'image' (base64 encoded image data)
    Returns: JSON with 'image' (base64 encoded image with background removed)
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "Missing 'image' in request body"}), 400
        
        # Decode base64 image
        image_data = data['image']
        if image_data.startswith('data:image'):
            # Handle data URL format
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Remove background using rembg
        output = rembg.remove(image)
        
        # Convert back to base64
        output_buffer = io.BytesIO()
        output.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        output_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            "success": True,
            "image": output_base64
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/remove-bg-url', methods=['POST'])
def remove_bg_url():
    """
    POST /remove-bg-url
    Body: JSON with 'url' (public image URL)
    Returns: JSON with 'image' (base64 encoded image with background removed)
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "Missing 'url' in request body"}), 400
        
        url = data['url']
        
        # Download image from URL
        import requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        image = Image.open(io.BytesIO(response.content))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Remove background using rembg
        output = rembg.remove(image)
        
        # Convert back to base64
        output_buffer = io.BytesIO()
        output.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        output_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            "success": True,
            "image": output_base64
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
