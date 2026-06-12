"""
========================================================================
  SAVVY SCANNER - Remove Background API
  Flask + rembg para iPhone
  Deploy: Railway.app (FREE)
========================================================================
"""

import os
import io
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS  # ← AGREGAR CORS
from PIL import Image, ImageEnhance

# Importar rembg
try:
    from rembg import remove
except ImportError:
    print("INSTALAR: pip install rembg pillow onnxruntime flask-cors")
    raise

app = Flask(__name__)
CORS(app)  # ← HABILITAR CORS EN TODA LA APP

# ── HEALTH CHECK ────────────────────────────────────────
@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status': 'online',
        'service': 'Savvy Scanner - Remove Background API',
        'version': '1.0'
    })

# ── REMOVE BACKGROUND ENDPOINT ──────────────────────────
@app.route('/remove-bg', methods=['POST', 'OPTIONS'])  # ← AGREGAR OPTIONS
def remove_background():
    """
    Recibe: JSON con imagen en Base64
    Procesa: Quita fondo con rembg
    Devuelve: PNG sin fondo en Base64
    
    Cliente:
    --------
    const res = await fetch('https://savvy-rembg.railway.app/remove-bg', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            image: 'data:image/jpeg;base64,/9j/4AAQ...'
        })
    });
    const data = await res.json();
    const pngUrl = 'data:image/png;base64,' + data.image;
    """
    
    try:
        # 1. PARSEAR REQUEST
        data = request.json
        if not data or 'image' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing "image" in request body'
            }), 400
        
        img_data = data['image']
        
        # Si viene como data:image/jpeg;base64,... extraer la parte base64
        if ',' in img_data:
            img_data = img_data.split(',')[1]
        
        # 2. DECODIFICAR BASE64 → PIL Image
        try:
            img_bytes = base64.b64decode(img_data)
            input_image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Invalid image format: {str(e)}'
            }), 400
        
        # 3. QUITAR FONDO con rembg
        output_image = remove(input_image)
        
        # 4. AUTO-CROP (igual que quitar_fondos.py)
        # Detectar bounding box del objeto
        bbox = output_image.getbbox()
        if bbox and bbox != (0, 0, output_image.width, output_image.height):
            # Calcular margen (2% del lado más pequeño)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            margin = max(5, int(min(width, height) * 0.02))
            
            # Crop con margen
            crop_box = (
                max(0, bbox[0] - margin),
                max(0, bbox[1] - margin),
                min(output_image.width, bbox[2] + margin),
                min(output_image.height, bbox[3] + margin)
            )
            output_image = output_image.crop(crop_box)
        
        # 5. AUMENTAR BRILLO 25% (igual que quitar_fondos.py)
        
        # 6. GUARDAR COMO PNG TRANSPARENTE
        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format='PNG', optimize=True)
        output_buffer.seek(0)
        
        # 7. CODIFICAR A BASE64
        result_b64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': result_b64,
            'format': 'png',
            'size': f'{output_image.width}x{output_image.height}',
            'message': 'Background removed successfully'
        })
    
    except Exception as e:
        print(f'❌ Error en /remove-bg: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ── REMOVE BACKGROUND BATCH ────────────────────────────
@app.route('/remove-bg-batch', methods=['POST', 'OPTIONS'])
def remove_background_batch():
    """
    Procesa múltiples imágenes
    Recibe: { images: [{ id: '1', image: 'base64...' }, ...] }
    Devuelve: { success: true, results: [...] }
    """
    try:
        data = request.json
        if not data or 'images' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing "images" in request body'
            }), 400
        
        images = data['images']
        results = []
        
        for img_obj in images:
            try:
                img_id = img_obj.get('id', 'unknown')
                img_data = img_obj.get('image', '')
                
                # Extraer base64
                if ',' in img_data:
                    img_data = img_data.split(',')[1]
                
                # Procesar
                img_bytes = base64.b64decode(img_data)
                input_image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
                output_image = remove(input_image)
                
                # Auto-crop
                bbox = output_image.getbbox()
                if bbox:
                    margin = max(5, int(min(bbox[2]-bbox[0], bbox[3]-bbox[1]) * 0.02))
                    crop_box = (
                        max(0, bbox[0] - margin),
                        max(0, bbox[1] - margin),
                        min(output_image.width, bbox[2] + margin),
                        min(output_image.height, bbox[3] + margin)
                    )
                    output_image = output_image.crop(crop_box)
                
                # Brillo
                
                # Guardar
                output_buffer = io.BytesIO()
                output_image.save(output_buffer, format='PNG', optimize=True)
                result_b64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
                
                results.append({
                    'id': img_id,
                    'image': result_b64,
                    'status': 'ok'
                })
            
            except Exception as e:
                results.append({
                    'id': img_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(images),
            'succeeded': len([r for r in results if r['status'] == 'ok'])
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ── SERVIDOR ────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
