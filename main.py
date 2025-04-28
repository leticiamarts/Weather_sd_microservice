import aiohttp
from aiohttp import web
import sqlite3
import datetime
import json
import os
from dotenv import load_dotenv
from aiohttp.web import Response
from pathlib import Path

load_dotenv()
API_KEY = os.getenv('OWM_API_KEY')
if not API_KEY:
    raise ValueError("API key não encontrada! Crie um arquivo .env com OWM_API_KEY")

def init_db():
    conn = sqlite3.connect('weather_cache.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS weather_data
                     (city TEXT PRIMARY KEY, 
                      data TEXT, 
                      timestamp TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_cached_data(city):
    conn = sqlite3.connect('weather_cache.db')
    cursor = conn.cursor()
    cursor.execute("SELECT data, timestamp FROM weather_data WHERE city = ?", (city,))
    result = cursor.fetchone()
    conn.close()
    return result

def update_cache(city, data):
    conn = sqlite3.connect('weather_cache.db')
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute("REPLACE INTO weather_data (city, data, timestamp) VALUES (?, ?, ?)", 
                   (city, json.dumps(data), timestamp))
    conn.commit()
    conn.close()

async def get_weather(request):
    city = request.query.get('city')
    if not city:
        return Response(text="Parâmetro 'city' obrigatório", status=400)
    
    cached = get_cached_data(city)
    if cached:
        data, timestamp = cached
        if (datetime.datetime.now() - datetime.datetime.fromisoformat(timestamp)).seconds < 3600:
            return web.json_response(json.loads(data))
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}'
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    update_cache(city, data)
                    return web.json_response(data)
                return Response(text="Erro ao buscar dados", status=500)
    except Exception as e:
        return Response(text=f"Erro: {str(e)}", status=500)

async def swagger_ui(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Weather Service API</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@3/swagger-ui.css">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
        <script>
            const ui = SwaggerUIBundle({
                url: '/swagger.yaml',
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout"
            })
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def serve_swagger_file(request):
    return web.FileResponse(Path(__file__).parent / 'swagger.yaml')

def setup_routes(app):
    app.router.add_get('/weather', get_weather)
    app.router.add_get('/docs', swagger_ui)
    app.router.add_get('/swagger.yaml', serve_swagger_file)

if __name__ == '__main__':
    app = web.Application()
    setup_routes(app)
    init_db()
    web.run_app(app, port=8080)