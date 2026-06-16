"""
========================================================================
  SAVVY SCANNER - Remove Background API + eBay Browse API (OAuth)
  Flask + rembg + eBay OAuth automático para iPhone
  Deploy: Railway.app (FREE)
========================================================================
"""

import os
import io
import base64
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image

# Importar rembg
try:
    from rembg import remove
except ImportError:
    print("INSTALAR: pip install rembg pillow onnxruntime flask-cors requests")
    raise

app = Flask(__name__)
CORS(app)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EBAY OAUTH MANAGER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EbayTokenManager:
    def __init__(self):
        self.app_id = 'StevenGa-SavvySca-PRD-8laddb012-655f2649'
        self.cert_id = 'PRD-1addb012c1l2-1d46-4c31-9731-99d5'
        self.access_token = None
        self.token_expiry = None
        self.oauth_url = 'https://api.ebay.com/identity/v1/oauth2/token'
        self.scopes = 'https://api.ebay.com/oauth/api_scope'
    
    def _get_client_credentials(self):
        """Basic Auth con App ID y Cert ID"""
        credentials = f'{self.app_id}:{self.cert_id}'
        encoded = base64.b64encode(credentials.encode()).decode()
        return f'Basic {encoded}'
    
    def generate_token(self):
        """Genera Application Token (no expira)"""
        print('🔑 [OAUTH] Generando Application Token...')
        try:
            headers = {
                'Authorization': self._get_client_credentials(),
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'client_credentials',
                'scope': self.scopes
            }
            
            response = requests.post(self.oauth_url, headers=headers, data=data, timeout=10)
            
            if response.status_code != 200:
                print(f'❌ [OAUTH] Error {response.status_code}: {response.text[:200]}')
                return False
            
            result = response.json()
            self.access_token = result.get('access_token')
            expires_in = result.get('expires_in', 7200)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            print(f'✅ [OAUTH] Token generado: {self.access_token[:30]}...')
            print(f'   Expira: {self.token_expiry}')
            return True
        
        except Exception as e:
            print(f'❌ [OAUTH] Error: {str(e)}')
            return False
    
    def get_valid_token(self):
        """Retorna token válido (genera uno nuevo si es necesario)"""
        # Si no hay token, generar
        if not self.access_token:
            self.generate_token()
            return self.access_token
        
        # Si expira en < 5 minutos, renovar
        if self.token_expiry and datetime.now() > (self.token_expiry - timedelta(minutes=5)):
            self.generate_token()
        
        return self.access_token

# Instancia global del manager
token_manager = EbayTokenManager()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status': 'online',
        'service': 'Savvy Scanner - Background Removal + eBay Search (OAuth)',
        'version': '3.0',
        'endpoints': [
            '/remove-bg (POST)',
            '/remove-bg-batch (POST)',
            '/ebay-search (GET)?upc=XXXXX or ?keywords=XXXXX'
        ]
    })

# ── REMOVE BACKGROUND ──────────────────────────────────
@app.route('/remove-bg', methods=['POST', 'OPTIONS'])
def remove_background():
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'Missing image'}), 400
        
        img_data = data['image']
        if ',' in img_data:
            img_data = img_data.split(',')[1]
        
        img_bytes = base64.b64decode(img_data)
        input_image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        output_image = remove(input_image)
        
        # Auto-crop with larger margin for clothing (prevent cutting sleeves)
        bbox = output_image.getbbox()
        if bbox and bbox != (0, 0, output_image.width, output_image.height):
            margin = max(50, int(min(bbox[2]-bbox[0], bbox[3]-bbox[1]) * 0.15))
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
        
        return jsonify({
            'success': True,
            'image': result_b64,
            'format': 'png',
            'size': f'{output_image.width}x{output_image.height}'
        })
    
    except Exception as e:
        print(f'❌ Error /remove-bg: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

# ── REMOVE BACKGROUND BATCH ────────────────────────────
@app.route('/remove-bg-batch', methods=['POST', 'OPTIONS'])
def remove_background_batch():
    try:
        data = request.json
        if not data or 'images' not in data:
            return jsonify({'success': False, 'error': 'Missing images'}), 400
        
        results = []
        for img_obj in data['images']:
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
                    margin = max(50, int(min(bbox[2]-bbox[0], bbox[3]-bbox[1]) * 0.15))
                    crop_box = (max(0, bbox[0]-margin), max(0, bbox[1]-margin),
                               min(output_image.width, bbox[2]+margin), min(output_image.height, bbox[3]+margin))
                    output_image = output_image.crop(crop_box)
                
                output_buffer = io.BytesIO()
                output_image.save(output_buffer, format='PNG', optimize=True)
                result_b64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
                
                results.append({'id': img_id, 'image': result_b64, 'status': 'ok'})
            
            except Exception as e:
                results.append({'id': img_id, 'status': 'error', 'error': str(e)})
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(data['images']),
            'succeeded': len([r for r in results if r['status'] == 'ok'])
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ── EBAY SEARCH (OAuth) ────────────────────────────────
@app.route('/ebay-search', methods=['GET'])
def ebay_search():
    """
    Busca en eBay usando Browse API con OAuth automático
    
    Uso:
    - /ebay-search?upc=198533572597
    - /ebay-search?keywords=shirt
    """
    try:
        upc = request.args.get('upc')
        keywords = request.args.get('keywords')
        
        if not upc and not keywords:
            return jsonify({
                'found': False,
                'error': 'Provide either "upc" or "keywords" parameter'
            }), 400
        
        query = upc if upc else keywords
        print(f'🔍 [SEARCH] Buscando: {query}')
        
        # Obtener token válido
        token = token_manager.get_valid_token()
        
        if not token:
            return jsonify({
                'found': False,
                'error': 'Failed to obtain OAuth token',
                'source': 'ebay_oauth'
            }), 500
        
        # Hacer búsqueda en eBay Browse API
        headers = {
            'Authorization': f'Bearer {token}',
            'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
            'X-EBAY-C-ENDUSERCTX': 'contextualshoppingflag,0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        url = 'https://api.ebay.com/buy/browse/v1/item_summary/search'
        params = {
            'q': query,
            'limit': '10',
            'filter': 'conditionIds:{1000}'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f'📥 [SEARCH] Status: {response.status_code}')
        
        if response.status_code != 200:
            print(f'❌ [SEARCH] Error: {response.text[:300]}')
            return jsonify({
                'found': False,
                'error': f'eBay returned {response.status_code}',
                'details': response.text[:500],
                'source': 'ebay_oauth'
            }), response.status_code
        
        data = response.json()
        items = data.get('itemSummaries', [])
        
        print(f'✅ [SEARCH] Encontrados {len(items)} items')
        
        # Procesar resultados
        result = {
            'found': len(items) > 0,
            'product': None,
            'topTitles': [],
            'pricing': {
                'active': {'low': 0, 'high': 0, 'median': 0},
                'sold': {'low': 0, 'high': 0, 'median': 0, 'count': 0}
            },
            'source': 'ebay_oauth'
        }
        
        if items:
            result['topTitles'] = [item.get('title') for item in items if item.get('title')]
            
            # Procesar primer item
            top_item = items[0]
            price = float(top_item.get('price', {}).get('value', 0))
            
            result['product'] = {
                'name': top_item.get('title', ''),
                'itemId': top_item.get('itemId', ''),
                'price': price,
                'condition': top_item.get('condition', 'New'),
                'currency': top_item.get('price', {}).get('currency', 'USD')
            }
            
            if price > 0:
                result['pricing']['active']['low'] = price
                result['pricing']['active']['high'] = price * 1.15
                result['pricing']['active']['median'] = price
                result['pricing']['sold']['low'] = price * 0.85
                result['pricing']['sold']['high'] = price * 1.15
                result['pricing']['sold']['median'] = price
                result['pricing']['sold']['count'] = 5
        
        return jsonify(result)
    
    except requests.exceptions.Timeout:
        return jsonify({
            'found': False,
            'error': 'Request timeout',
            'source': 'ebay_oauth'
        }), 504
    
    except Exception as e:
        print(f'❌ Error /ebay-search: {str(e)}')
        return jsonify({
            'found': False,
            'error': str(e),
            'source': 'ebay_oauth'
        }), 500

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SERVIDOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
