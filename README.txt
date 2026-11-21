GREEN HERO - Deploy on Render
1. Upload index.html, server.py, requirements.txt to a GitHub repository.
2. Render > New > Web Service > connect repository.
3. Runtime: Python; Build Command: pip install -r requirements.txt
4. Start Command: python server.py
5. Environment: GOOGLE_TTS_API_KEY = your Google Cloud key
6. Deploy and visit the Render URL.
The server uses the Render PORT environment variable and serves HTML and /api/tts together.
Google Cloud billing may be required. Configure API restrictions and billing alerts.
Do not commit keys to GitHub or HTML. On Render free services may spin down when idle.
Note: this is a starter deployment for small-scale school demonstrations, not a hardened production service.
