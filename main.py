"""
========================================================================
  SAVVY SCANNER - Remove Background API + eBay Search
  Flask + rembg + web scraping para iPhone
  Deploy: Railway.app (FREE)
========================================================================
"""

import os
import io
import base64
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageEnhance

# Importar rembg
try:
    from rembg import remove
except ImportError:
    print("INSTALAR: pip install rembg pillow onnxruntime flask-cors requests")
    raise

app = Flask(__name__)
CORS(app)

# ── HEALTH CHECK ────────────────────────────────────────
@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status': 'online',
        'service': 'Savvy Scanner - Remove Background API + eBay Search',
        'version': '2.0',
        'endpoints': [
            '/remove-bg (POST)',
            '/remove-bg-batch (POST)',
            '/ebay-search (GET)?upc=XXXXX or ?keywords=XXXXX'
        ]
    })

# ── REMOVE BACKGROUND ENDPOINT ──────────────────────────
@app.route('/remove-bg', methods=['POST', 'OPTIONS'])
def remove_background():
    """
    Recibe: JSON con imagen en Base64
    Procesa: Quita fondo con rembg
    Devuelve: PNG sin fondo en Base64
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
        
        # 4. AUTO-CROP
        bbox = output_image.getbbox()
        if bbox and bbox != (0, 0, output_image.width, output_image.height):
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            margin = max(5, int(min(width, height) * 0.02))
            
            crop_box = (
                max(0, bbox[0] - margin),
                max(0, bbox[1] - margin),
                min(output_image.width, bbox[2] + margin),
                min(output_image.height, bbox[3] + margin)
            )
            output_image = output_image.crop(crop_box)
        
        # 5. GUARDAR COMO PNG TRANSPARENTE
        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format='PNG', optimize=True)
        output_buffer.seek(0)
        
        # 6. CODIFICAR A BASE64
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
                
                if ',' in img_data:
                    img_data = img_data.split(',')[1]
                
                img_bytes = base64.b64decode(img_data)
                input_image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
                output_image = remove(input_image)
                
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

# ── EBAY SEARCH ENDPOINT ────────────────────────────────
@app.route('/ebay-search', methods=['GET'])
def ebay_search():
    """
    Busca en eBay por UPC o keywords
    
    Uso:
    - /ebay-search?upc=198533572597
    - /ebay-search?keywords=shirt
    
    Retorna: { found, product, topTitles, pricing }
    """
    try:
        upc = request.args.get('upc')
        keywords = request.args.get('keywords')
        
        if not upc and not keywords:
            return jsonify({
                'success': False,
                'error': 'Provide either "upc" or "keywords" parameter'
            }), 400
        
        # Construir URL de búsqueda en eBay
        search_url = 'https://www.ebay.com/sch/i.html'
        params = {
            '_nkw': upc if upc else keywords,
            '_sacat': '0',
            '_from': 'R40',
            'rt': 'nc'
        }
        
        print(f'🔍 Buscando en eBay: {params["_nkw"]}')
        
        # Hacer solicitud con User-Agent realista
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
        
        res = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if res.status_code != 200:
            return jsonify({
                'found': False,
                'error': f'eBay returned {res.status_code}',
                'source': 'ebay_search'
            }), res.status_code
        
        # Parsear HTML
        result = parse_ebay_html(res.text, upc if upc else keywords)
        
        return jsonify(result)
    
    except requests.exceptions.Timeout:
        return jsonify({
            'found': False,
            'error': 'Request timeout',
            'source': 'ebay_search'
        }), 504
    
    except Exception as e:
        print(f'❌ Error en /ebay-search: {str(e)}')
        return jsonify({
            'found': False,
            'error': str(e),
            'source': 'ebay_search'
        }), 500

# ── PARSER HTML ─────────────────────────────────────────
def parse_ebay_html(html, query):
    """
    Extrae datos de la página HTML de eBay
    """
    result = {
        'found': False,
        'product': None,
        'topTitles': [],
        'pricing': {
            'active': {'low': 0, 'high': 0, 'median': 0},
            'sold': {'low': 0, 'high': 0, 'median': 0, 'count': 0}
        },
        'source': 'ebay_search'
    }
    
    try:
        import re
        
        # Buscar items en el HTML
        # Patrón 1: data-component-type="s-search-result"
        item_pattern = r'<div[^>]*data-component-type="s-search-result"[^>]*>[\s\S]*?(?=<div[^>]*data-component-type="s-search-result"|$)'
        items = re.findall(item_pattern, html)
        
        print(f'📦 Encontrados {len(items)} items (patrón 1)')
        
        # Si no hay items, intentar patrón alternativo
        if not items:
            item_pattern = r'<span[^>]*role="heading"[^>]*>([^<]+)<\/span>'
            titles = re.findall(item_pattern, html)
            print(f'📦 Encontrados {len(titles)} títulos (patrón 2)')
            
            if titles:
                result['found'] = True
                result['topTitles'] = titles[:5]
                
                # Buscar primer precio
                price_pattern = r'\$[\d,]+\.?\d{0,2}'
                prices = re.findall(price_pattern, html)
                if prices:
                    try:
                        price = float(prices[0].replace('$', '').replace(',', ''))
                        result['product'] = {
                            'name': titles[0],
                            'price': price,
                            'condition': 'New',
                            'currency': 'USD'
                        }
                        result['pricing']['active']['low'] = price
                        result['pricing']['active']['high'] = price * 1.15
                        result['pricing']['active']['median'] = price
                    except:
                        pass
        
        else:
            # Procesar items encontrados
            result['found'] = True
            
            for i, item_html in enumerate(items[:5]):
                try:
                    # Extraer título
                    title_match = re.search(r'<span[^>]*role="heading"[^>]*>([^<]+)<\/span>', item_html)
                    if not title_match:
                        title_match = re.search(r'<h3[^>]*>([^<]+)<\/h3>', item_html)
                    
                    title = title_match.group(1).strip() if title_match else 'Unknown'
                    
                    # Extraer precio
                    price_match = re.search(r'\$[\d,]+\.?\d{0,2}', item_html)
                    price = 0
                    if price_match:
                        price_str = price_match.group(0).replace('$', '').replace(',', '')
                        try:
                            price = float(price_str)
                        except:
                            price = 0
                    
                    result['topTitles'].append(title)
                    
                    if i == 0:
                        # Primer item (el mejor resultado)
                        result['product'] = {
                            'name': title,
                            'price': price,
                            'condition': 'New',
                            'currency': 'USD'
                        }
                        
                        if price > 0:
                            result['pricing']['active']['low'] = price
                            result['pricing']['active']['high'] = price * 1.15
                            result['pricing']['active']['median'] = price
                            result['pricing']['sold']['low'] = price * 0.85
                            result['pricing']['sold']['high'] = price * 1.15
                            result['pricing']['sold']['median'] = price
                            result['pricing']['sold']['count'] = 5
                
                except Exception as e:
                    print(f'⚠️ Error al procesar item {i}: {str(e)}')
                    continue
        
        print(f'✅ Parseo completado: found={result["found"]}, items={len(result["topTitles"])}')
        return result
    
    except Exception as e:
        print(f'❌ Error en parse_ebay_html: {str(e)}')
        return result

# ── SERVIDOR ────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
