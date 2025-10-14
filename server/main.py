# -*- Code revised September 2025. wlrnoodle. -*-
# this is the main file for the DispatchPi flask app

from flask import Flask, send_file, redirect, session , url_for, request
import os
import requests
import json
from io import BytesIO
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from eink_image import Image_transform
from gmail_connector_no_queue import Gmail_connector

# Error handling imports
from googleapiclient.errors import HttpError
from PIL import UnidentifiedImageError
from requests.exceptions import RequestException

# Paths to secrets and token files
dir_path = os.path.dirname(os.path.realpath(__file__))
CLIENT_SECRETS_FILE = os.path.join(dir_path, "secrets/client_secret.json")
TOKEN_FILE = os.path.join(dir_path, 'secrets/token.json')
FLASK_KEY = os.path.join(dir_path, 'secrets/flask_key.json')

# OAuth 2.0 scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Flask app
app = Flask(__name__)

# Load Flask app key
with open(FLASK_KEY) as secrets_file:
    key_file = json.load(secrets_file)
    app.secret_key = key_file['SECRET_KEY']

def generate_credentials():
    """Generate or refresh OAuth 2.0 credentials."""
    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not credentials.valid:
            credentials.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(credentials.to_json())
        return credentials
    return None

def pull_and_display_image(frame_type, creds):
    """Pull an image from Gmail and display it."""
    try:
        # Initialize Gmail connector
        gmail_inbox = Gmail_connector(creds=creds, satellite_emails=["of8179333@gmail.com"])

        # Pull attachments from Gmail - always use 'me' as userID for Gmail API
        gmail_inbox.pull_attachments("me")

        # Get the first image and its text - use frame_type to determine which images to show
        image_to_send, output_text = gmail_inbox.grab_first_image(frame_type, "me")

        # Transform the image for the e-ink display
        transformed_image = Image_transform(imported_image=image_to_send, fit="crop", message=output_text).render()
        output = BytesIO()
        transformed_image.save(output, "PNG")
        output.seek(0)
        return output

    except HttpError as e:
        print(f"Gmail API error: {e}")
        return None  # Return None or handle the error appropriately

    except UnidentifiedImageError as e:
        print(f"Image processing error: {e}")
        return None  # Return None or handle the error appropriately

    except RequestException as e:
        print(f"Network error: {e}")
        return None  # Return None or handle the error appropriately

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None  # Return None or handle the error appropriately

@app.route('/')
def index():
    return ('<table>' +
            "<tr><td><a href='/satellite_frame'>See the satellite's frame</a></td>" +
            "<tr><td><a href='/earth_frame'>See the earth's frame</a></td>" +
            '<tr><td><a href="/authorize">Test the auth flow directly. You will be sent back to the index</a></td>' +
            '<tr><td><a href="/revoke">Revoke current credentials</a></td>' +
            '</td></tr></table>')

@app.route('/satellite_frame')
def api_route_satellite_frame():
    if os.path.exists(TOKEN_FILE):
        credentials = generate_credentials()
    else:
        session['view'] = "satellite_frame"
        return redirect('authorize')

    output = pull_and_display_image(frame_type="satellite_frame", creds=credentials)
    if output:
        return send_file(output, mimetype="image/png")
    else:
        return "Failed to retrieve image. Please try again later.", 500

@app.route('/earth_frame')
def api_route_earth_frame():
    if os.path.exists(TOKEN_FILE):
        credentials = generate_credentials()
    else:
        session['view'] = "earth_frame"
        return redirect('authorize')

    output = pull_and_display_image(frame_type="earth_frame", creds=credentials)
    if output:
        return send_file(output, mimetype="image/png")
    else:
        return "Failed to retrieve image. Please try again later.", 500

@app.route('/authorize')
def authorize():
    if 'view' not in session:
        session['view'] = "index"

    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not credentials.valid:
            credentials.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(credentials.to_json())
        return redirect(url_for('index'))
    else:
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
        flow.redirect_uri = url_for('oauth2callback', _external=True)
        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='false')
        session['state'] = state
        return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    with open(TOKEN_FILE, 'w') as token:
        token.write(credentials.to_json())
    return redirect(url_for('index'))

@app.route('/revoke')
def revoke():
    credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    revoke = requests.post('https://oauth2.googleapis.com/revoke',
                           params={'token': credentials.token},
                           headers={'content-type': 'application/x-www-form-urlencoded'})
    if revoke.status_code == 200:
        return 'Credentials successfully revoked.' + index()
    else:
        return 'An error occurred.' + index()

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run('localhost', 8080, debug=True)