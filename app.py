from flask import Flask, render_template, redirect, request, session, make_response, jsonify
from constants import SSK, SPOTIFY_REDIRECT_URL, SPOTIFY_CLIENT_SECRET, SPOTIFY_CLIENT_ID, PORT, SCOPE, FEATURES_REQUEST_MAX, USE_FEATURES, TRACK_SEED, ARTIST_SEED, MAX_TRACKS_IN_PLAYLIST
import spotipy
import time
import random
from queue import PriorityQueue

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

@app.route("/generatePlaylist", methods=['POST', 'OPTIONS'])
def generatePlaylist():
    if request.method == "OPTIONS":
        return preflightResponse()

    data = request.json
    playlistId = data['playlistId']
    print('input: ', playlistId)
        
    session['token_info'], authorized = getValidToken(session)
    session.modified = True

    if not authorized:
        json = { 'success': False }

    else:
        token = session.get('token_info').get('access_token')
        sp = spotipy.Spotify(auth=token)
        username = sp.current_user()['id']
        trackIds, artistIds = getSeedsFromPlaylist(playlistId, sp)
        recommendedTrackIds = [trackId for trackId in getRecommendedSongs(trackIds, artistIds, sp) if trackId not in trackIds]
        addToPlaylist(sp, recommendedTrackIds, username, playlistId)
        print('output', recommendedTrackIds)
        json = { 'success': True }
    
    return createResponse(json)

def addToPlaylist(sp, trackIds, username, playlistId):
    if len(trackIds) > 0:
        sp.user_playlist_add_tracks(
            user=username,
            playlist_id=playlistId,
            tracks=rankByBPM(trackIds, sp)
        )

def getTrackFeatures(tracks, sp):
    features = []

    for offset in range(0, len(tracks), FEATURES_REQUEST_MAX):
        songFeaturesToRequest = []

        # divide into FEATURES_REQUEST_MAX size chunks
        for track in tracks[offset:offset + FEATURES_REQUEST_MAX]:
            songFeaturesToRequest.append(track['id'])

        features += sp.audio_features(
            tracks=songFeaturesToRequest)

    return features

def getFeatureArguments(features):
    acousticness = []
    danceability = []
    energy = []
    instrumentalness = []
    liveness = []
    loudness = []
    speechiness = []
    tempo = []
    valence = []

    for feature in features:
        acousticness.append(feature['acousticness'])
        danceability.append(feature['danceability'])
        energy.append(feature['energy'])
        instrumentalness.append(feature['instrumentalness'])
        liveness.append(feature['liveness'])
        loudness.append(feature['loudness'])
        speechiness.append(feature['speechiness'])
        tempo.append(feature['tempo'])
        valence.append(feature['valence'])

    return {
        'min_acousticness' : min(acousticness),
        'max_acousticness' : max(acousticness),
        'target_acousticness' : sum(acousticness) / len(acousticness),
        'min_danceability' : min(danceability),
        'max_danceability' : max(danceability),
        'target_danceability' : sum(danceability) / len(danceability),
        'min_energy' : min(energy),
        'max_energy' : max(energy),
        'target_energy' : sum(energy) / len(energy),
        'min_instrumentalness' : min(instrumentalness),
        'max_instrumentalness' : max(instrumentalness),
        'target_instrumentalness' : sum(instrumentalness) / len(instrumentalness),
        'min_liveness' : min(liveness),
        'max_liveness' : max(liveness),
        'target_liveness' : sum(liveness) / len(liveness),
        'min_loudness' : min(loudness),
        'max_loudness' : max(loudness),
        'target_loudness' : sum(loudness) / len(loudness),
        'min_speechiness' : min(speechiness),
        'max_speechiness' : max(speechiness),
        'target_speechiness' : sum(speechiness) / len(speechiness),
        'min_tempo' : min(tempo),
        'max_tempo' : max(tempo),
        'target_tempo' : sum(tempo) / len(tempo),
        'min_valence' : min(valence),
        'max_valence' : max(valence),
        'target_valence' : sum(valence) / len(valence),
    }

def rankByBPM(trackIds, sp):
    tracks = sp.tracks(trackIds)['tracks']
    features = getTrackFeatures(tracks, sp)

    sortedByBPM = PriorityQueue()
    for feature in features:
        trackId = feature['id']
        bpm = feature['tempo']
        sortedByBPM.put((bpm, trackId))

    results = []
    while not sortedByBPM.empty():
        tuplePair = sortedByBPM.get()
        print(tuplePair)
        results.append(tuplePair[1])

    return results

def getSeedsFromPlaylist(playlistId, sp):
    items = sp.playlist_tracks(playlistId)['items']
    trackIds = [item['track']['id'] for item in items]
    artistIds = [item['track']['artists'][0]['id'] for item in items]
    return trackIds, artistIds

def getRecommendedSongs(trackIds, artistIds, sp):
    if trackIds == 0:
        return []

    tracks = sp.tracks(trackIds)['tracks']
    features = getTrackFeatures(tracks, sp)
    featureArguments = getFeatureArguments(features)
    print(artistIds)

    if USE_FEATURES:
        recommendedTracks = sp.recommendations(
            seed_artists=random.sample(artistIds, min(len(artistIds), ARTIST_SEED)),
            seed_tracks=random.sample(trackIds, min(len(trackIds), TRACK_SEED)),
            limit=100,
            country=None,
            min_acousticness=featureArguments['min_acousticness'],
            max_acousticness=featureArguments['max_acousticness'],
            target_acousticness=featureArguments['target_acousticness'],
            min_danceability=featureArguments['min_danceability'],
            max_danceability=featureArguments['max_danceability'],
            target_danceability=featureArguments['target_danceability'],
            min_energy=featureArguments['min_energy'],
            max_energy=featureArguments['max_energy'],
            target_energy=featureArguments['target_energy'],
            # min_instrumentalness=featureArguments['min_instrumentalness'],
            # max_instrumentalness=featureArguments['max_instrumentalness'],
            # target_instrumentalness=featureArguments['target_instrumentalness'],
            # min_liveness=featureArguments['min_liveness'],
            # max_liveness=featureArguments['max_liveness'],
            # target_liveness=featureArguments['target_liveness'],
            # min_loudness=featureArguments['min_loudness'],
            # max_loudness=featureArguments['max_loudness'],
            # target_loudness=featureArguments['target_loudness'],
            # min_speechiness=featureArguments['min_speechiness'],
            # max_speechiness=featureArguments['max_speechiness'],
            # target_speechiness=featureArguments['target_speechiness'],
            min_tempo=featureArguments['min_tempo'],
            max_tempo=featureArguments['max_tempo'],
            target_tempo=featureArguments['target_tempo'],
            min_valence=featureArguments['min_valence'],
            max_valence=featureArguments['max_valence'],
            target_valence=featureArguments['target_valence']
        )
    
    else:
        recommendedTracks = sp.recommendations(
            None,
            None,
            seed_tracks=trackIds,
            limit=100,
            country=None
        )

    recommendedTrackIds = [recommendedTrack['id'] for recommendedTrack in recommendedTracks['tracks']]

    # filter out tracks already in the playlist and limit entire playlist to 50 tracks
    recommendedTrackIds = [trackId for trackId in recommendedTrackIds if trackId not in trackIds]
    tracksToAdd = MAX_TRACKS_IN_PLAYLIST - len(trackIds)
    if len(recommendedTrackIds) >= tracksToAdd:
        return recommendedTrackIds[0: tracksToAdd]
    return recommendedTrackIds




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
