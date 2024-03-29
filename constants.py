import os

# spotify security scopes
SCOPE = 'user-library-read playlist-read-private playlist-modify-private playlist-modify-public'

# Server-side Parameters
PORT = os.environ['PORT']

# spotify app credentials
SPOTIFY_CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']
SPOTIFY_REDIRECT_URL = os.environ['SPOTIFY_REDIRECT_URL']
SSK = os.environ['SSK']

# limits
FEATURES_REQUEST_MAX = 50
USE_FEATURES = os.environ['USE_FEATURES'].lower() == 'true'
TRACK_SEED = 3
ARTIST_SEED = 2
MAX_TRACKS_IN_PLAYLIST = 50