import os

# spotify security scopes
SCOPE = 'user-read-currently-playing user-read-playback-state'

# Server-side Parameters
PORT = os.environ['PORT']

# spotify app credentials
SPOTIFY_CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']
SPOTIFY_REDIRECT_URL = os.environ['SPOTIFY_REDIRECT_URL']
SSK = os.environ['SSK']