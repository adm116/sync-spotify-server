from flask import Flask, render_template, redirect, request, session, make_response, jsonify
from constants import *
import spotipy
import time
from flask_cors import CORS, cross_origin

app = Flask(__name__)
app.secret_key = SSK

whitelist = ['http://localhost:3000']

@app.after_request
def add_cors_headers(response):
    r = request.referrer[:-1]
    print(r)
    if r in whitelist:
        response.headers.add('Access-Control-Allow-Origin', r)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Headers', 'Cache-Control')
        response.headers.add('Access-Control-Allow-Headers', 'X-Requested-With')
        response.headers.add('Access-Control-Allow-Headers', 'Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
    return response

@app.route("/authUrl")
def authUrl():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URL, scope=SCOPE)
    auth_url = sp_oauth.get_authorize_url()
    json = {
        'auth_url': auth_url
    }
    
    return jsonify(json)


@app.route("/login", methods=['POST'])
def login():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URL, scope=SCOPE)
    session.clear()

    data = request.get_json()
    code = data['code']
    token_info = sp_oauth.get_access_token(code=code, check_cache=False)

    # Saving the access token along with all other token related info
    session['token_info'] = token_info
    session.modified = True

    return jsonify('')


# don't need this
@app.route("/refreshToken")
def refreshToken():
    session['token_info'], authorized = get_token(session)
    session.modified = True
    if not authorized:
        json = { 'success': False, 'token': '', 'expires_in': 0 }
    else:
        json = { 'success': True, 'token': session['token_info']['access_token'], 'expires_in': session['token_info']['expires_in'] }

    return jsonify(json)

# Checks to see if token is valid and gets a new token if not


def get_token(session):
    token_valid = False
    token_info = session.get("token_info", {})

    # Checking if the session already has a token stored
    if not (session.get('token_info', False)):
        token_valid = False
        return token_info, token_valid

    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URL, scope=SCOPE)
    token_info = sp_oauth.refresh_access_token(
        session.get('token_info').get('refresh_token'))

    token_valid = True
    return token_info, token_valid


if __name__ == "__main__":
    app.run(debug=True, port=PORT)
