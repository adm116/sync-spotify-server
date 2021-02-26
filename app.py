from flask import Flask, render_template, redirect, request, session, make_response, jsonify
from constants import SSK, SPOTIFY_REDIRECT_URL, SPOTIFY_CLIENT_SECRET, SPOTIFY_CLIENT_ID, PORT, SCOPE
import spotipy
import time

app = Flask(__name__)
app.secret_key = SSK

def addHeaders(response):
    response.headers.add("Access-Control-Allow-Origin", SPOTIFY_REDIRECT_URL)
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

def createResponse(json):
    response = jsonify(json)
    return addHeaders(response)

def preflightResponse():
    response = make_response()
    return addHeaders(response)

@app.route("/authUrl")
def authUrl():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URL, scope=SCOPE)
    auth_url = sp_oauth.get_authorize_url()
    json = {
        'auth_url': auth_url
    }
    
    return createResponse(json)


@app.route("/login", methods=['POST', 'OPTIONS'])
def login():
    if request.method == "OPTIONS":
        return preflightResponse()
        
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

    spotipyClass = spotipy.Spotify(
        auth=session.get('token_info').get('access_token'))
    currentUser = spotipyClass.current_user()

    # TODO: check for errors
    return createResponse(currentUser)

@app.route("/logout", methods=['POST', 'OPTIONS'])
def logout():
    if request.method == "OPTIONS":
        return preflightResponse()

    session.clear()
    session.modified = True

    # TODO: return something more useful here
    return createResponse('')

@app.route("/getToken", methods=['GET', 'OPTIONS'])
def getToken():
    if request.method == "OPTIONS":
        return preflightResponse()

    session['token_info'], authorized = getValidToken(session)
    session.modified = True
    if not authorized:
        json = { 'success': False, 'token': '', 'expires_in': 0 }
    else:
        json = { 'success': True, 'token': session['token_info']['access_token'], 'expires_in': session['token_info']['expires_in'] }

    return createResponse(json)

# Checks to see if token is valid and gets a new token if not
def getValidToken(session):
    token_valid = False
    token_info = session.get("token_info", {})

    # Checking if the session already has a token stored
    if not (session.get('token_info', False)):
        token_valid = False
        return token_info, token_valid

    # Checking if token has expired
    now = int(time.time())
    is_token_expired = session.get('token_info').get('expires_at') - now < 60

    # Refreshing token if it has expired
    if (is_token_expired):
        # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
        sp_oauth = spotipy.oauth2.SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URL, scope=SCOPE)
        token_info = sp_oauth.refresh_access_token(
            session.get('token_info').get('refresh_token'))

    token_valid = True
    return token_info, token_valid


if __name__ == "__main__":
    app.run(debug=True, port=PORT)
