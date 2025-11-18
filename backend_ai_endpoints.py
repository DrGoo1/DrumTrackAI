"""
Backend AI API Endpoints - Production Integration
Adds AI-powered pattern generation to DrumTracKAI backend
"""

from aiohttp import web
import json
import base64
from ai_pattern_generator import AIPatternGenerator
from drummer_categories import get_category_service
from drummer_profile_maturity import get_maturity_tracker, get_maturity_badge, get_maturity_color
import asyncio
from functools import partial

# Global AI generator instance
ai_generator = None

def initialize_ai_generator():
    """Initialize AI generator (call on server startup)"""
    global ai_generator
    try:
        ai_generator = AIPatternGenerator()
        print("✅ AI Pattern Generator initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize AI generator: {e}")
        return False

async def handle_ai_generate(request):
    """
    POST /api/ai/generate
    
    Generate AI drum pattern
    
    Body:
    {
        "tempo": 156.0,
        "style": "rock",
        "section": "verse",
        "complexity": 0.6,
        "creativity": 0.5,
        "drummer_profile": "jeff_porcaro"
    }
    """
    try:
        data = await request.json()
        
        # Extract parameters with defaults
        tempo = data.get('tempo', 120.0)
        style = data.get('style', 'rock')
        section = data.get('section', 'verse')
        complexity = data.get('complexity', 0.5)
        creativity = data.get('creativity', 0.5)
        drummer_profile = data.get('drummer_profile', None)
        
        # Generate pattern in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                ai_generator.generate_ai_pattern,
                tempo=tempo,
                style=style,
                section=section,
                complexity=complexity,
                creativity=creativity,
                drummer_profile=drummer_profile
            )
        )
        
        return web.json_response({
            'success': True,
            'pattern': result,
            'message': 'AI pattern generated successfully'
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_ai_interpolate(request):
    """
    POST /api/ai/interpolate
    
    Interpolate between two patterns
    
    Body:
    {
        "pattern1_id": "uploads/pattern1.mid",
        "pattern2_id": "uploads/pattern2.mid",
        "steps": 5
    }
    """
    try:
        data = await request.json()
        
        # TODO: Load patterns from IDs
        # For now, return placeholder
        
        return web.json_response({
            'success': True,
            'message': 'Interpolation endpoint (coming soon)'
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_ai_blend(request):
    """
    POST /api/ai/blend
    
    Blend multiple patterns with weights
    
    Body:
    {
        "pattern_ids": ["id1", "id2", "id3"],
        "weights": [0.5, 0.3, 0.2]
    }
    """
    try:
        data = await request.json()
        
        # TODO: Load patterns and blend
        # For now, return placeholder
        
        return web.json_response({
            'success': True,
            'message': 'Blend endpoint (coming soon)'
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_ai_status(request):
    """
    GET /api/ai/status
    
    Get AI system status
    """
    try:
        if ai_generator is None:
            return web.json_response({
                'success': False,
                'initialized': False,
                'message': 'AI generator not initialized'
            })
        
        return web.json_response({
            'success': True,
            'initialized': True,
            'model': {
                'name': 'GrooVAE',
                'latent_dim': 64,
                'hidden_dim': 512,
                'device': str(ai_generator.device)
            },
            'database': {
                'connected': True,
                'path': ai_generator.db_path
            }
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_ai_styles(request):
    """
    GET /api/ai/styles
    
    Get available styles from database
    """
    try:
        # Query unique styles
        ai_generator.cursor.execute("""
            SELECT DISTINCT style, COUNT(*) as count
            FROM drum_patterns
            WHERE style IS NOT NULL AND style != ''
            GROUP BY style
            ORDER BY count DESC
        """)
        
        rows = ai_generator.cursor.fetchall()
        
        styles = [
            {'name': row[0], 'count': row[1]}
            for row in rows
        ]
        
        return web.json_response({
            'success': True,
            'styles': styles,
            'total_patterns': sum(s['count'] for s in styles)
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_ai_drummer_categories(request):
    """
    GET /api/ai/drummer-categories
    
    Get available drummer categories
    """
    try:
        category_service = get_category_service()
        categories = category_service.list_categories()
        
        return web.json_response({
            'success': True,
            'count': len(categories),
            'categories': categories
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_ai_category_drummers(request):
    """
    GET /api/ai/drummers/{category_id}
    
    Get drummers in a specific category
    """
    try:
        category_id = request.match_info.get('category_id')
        category_service = get_category_service()
        
        category = category_service.get_category(category_id)
        if not category:
            return web.json_response({
                'success': False,
                'error': f'Category not found: {category_id}'
            }, status=404)
        
        drummers = category_service.list_drummers_in_category(category_id)
        
        return web.json_response({
            'success': True,
            'category': {
                'id': category['id'],
                'display_name': category['display_name'],
                'icon': category['icon'],
                'color': category['color']
            },
            'drummers': drummers
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_ai_drummer_maturity(request):
    """
    GET /api/ai/drummer-maturity/{drummer_id}
    
    Get maturity info for a specific drummer
    """
    try:
        drummer_id = request.match_info.get('drummer_id')
        maturity_tracker = get_maturity_tracker()
        
        maturity = maturity_tracker.get_profile_maturity(drummer_id)
        
        return web.json_response({
            'success': True,
            'maturity': {
                **maturity,
                'badge': get_maturity_badge(maturity['maturity_level']),
                'color': get_maturity_color(maturity['maturity_level'])
            }
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_ai_all_maturity(request):
    """
    GET /api/ai/maturity-stats
    
    Get maturity stats for all drummers
    """
    try:
        maturity_tracker = get_maturity_tracker()
        stats = maturity_tracker.get_all_maturity_stats()
        
        # Add badges and colors
        for stat in stats:
            stat['badge'] = get_maturity_badge(stat['maturity_level'])
            stat['color'] = get_maturity_color(stat['maturity_level'])
        
        return web.json_response({
            'success': True,
            'count': len(stats),
            'drummers': stats
        })
    
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

# Routes to add to main app
def setup_ai_routes(app):
    """Add AI routes to aiohttp app"""
    app.router.add_post('/api/ai/generate', handle_ai_generate)
    app.router.add_post('/api/ai/interpolate', handle_ai_interpolate)
    app.router.add_post('/api/ai/blend', handle_ai_blend)
    app.router.add_get('/api/ai/status', handle_ai_status)
    app.router.add_get('/api/ai/styles', handle_ai_styles)
    app.router.add_get('/api/ai/drummer-categories', handle_ai_drummer_categories)
    app.router.add_get('/api/ai/drummers/{category_id}', handle_ai_category_drummers)
    app.router.add_get('/api/ai/drummer-maturity/{drummer_id}', handle_ai_drummer_maturity)
    app.router.add_get('/api/ai/maturity-stats', handle_ai_all_maturity)
    
    print("✅ AI API routes registered")

# For testing
if __name__ == "__main__":
    import aiohttp_cors
    
    # Initialize
    initialize_ai_generator()
    
    # Create app
    app = web.Application()
    setup_ai_routes(app)
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    
    # Configure CORS on all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Run
    print("\n🚀 Starting AI API test server...")
    print("   http://localhost:8001")
    web.run_app(app, host='0.0.0.0', port=8001)
