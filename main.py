import os
import base64
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageEnhance
import rembg

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/remove-bg', methods=['POST', 'OPTIONS'])
def remove_bg():
    """
    POST /remove-bg
    Body: JSON with 'image' (base64 encoded image data)
    Returns: JSON with 'image' (base64 encoded image with background removed)
    """
    if request.method == 'OPTIONS':
        return '', 204
    
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
        
        # Auto-crop: trim transparent space around the product
        bbox = output.getbbox()
        if bbox:
            # Add small margin (2% of the smallest dimension)
            margin = max(5, int(min(bbox[2]-bbox[0], bbox[3]-bbox[1]) * 0.02))
            crop_box = (
                max(0, bbox[0] - margin),
                max(0, bbox[1] - margin),
                min(output.width, bbox[2] + margin),
                min(output.height, bbox[3] + margin)
            )
            output = output.crop(crop_box)
        
        # Increase brightness 25%
        enhancer = ImageEnhance.Brightness(output)
        output = enhancer.enhance(1.25)
        
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
        
        # Auto-crop: trim transparent space
        bbox = output.getbbox()
        if bbox:
            margin = max(5, int(min(bbox[2]-bbox[0], bbox[3]-bbox[1]) * 0.02))
            crop_box = (
                max(0, bbox[0] - margin),
                max(0, bbox[1] - margin),
                min(output.width, bbox[2] + margin),
                min(output.height, bbox[3] + margin)
            )
            output = output.crop(crop_box)
        
        # Increase brightness 25%
        enhancer = ImageEnhance.Brightness(output)
        output = enhancer.enhance(1.25)
        
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
