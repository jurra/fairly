import os
import yaml
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

import vcr

import pytest
import fairly

# Requires develop to have .env file with FAIRLY_FIGSHARE_TOKEN
FIGSHARE_TOKEN = os.environ.get("FAIRLY_FIGSHARE_TOKEN")
ZENODO_TOKEN = os.environ.get("FAIRLY_ZENODO_TOKEN")

# load clients from supported clients
TEMPLATES = os.listdir("./src/fairly/data/templates")

# We generate a unique string that we can use to populate metadata for testing
ustring = str(uuid.uuid4())

def setup_fairly_config_for_testing():
    """Create a fairly config file for testing
    for this we need to create also the directory where the config file is stored
    We also create a backup of the config file before running the tests to recover prior existing config
    """
    # User might not have a fairly config file
    try: 
        if not os.path.exists(os.path.expanduser("~/.fairly")):
            os.makedirs(os.path.expanduser("~/.fairly"))
    except: print("Could not create ~/.fairly folder, check for premisions or if the folder already exists")
       
    # If user has a config file we backup it
    # We do this to test the config file creation and loading
    try: 
        config = {}

        # Create the config file if it does not exist using environment variables
        if not os.path.exists(os.path.expanduser("~/.fairly/config.json")):
            with open(os.path.expanduser("~/.fairly/config.json"), "w") as f:
                # create dummy config file using environment variables
                config['4tu'] = { 'token' : FIGSHARE_TOKEN }
                config['zenodo'] = { 'token' : ZENODO_TOKEN }
                f.write(json.dumps(config))
        else: 
            # Otherwise we use the existing config file and backup it
            with open(os.path.expanduser("~/.fairly/config.json"), "r") as f:
                config = json.load(f)

        with open(os.path.expanduser("~/.fairly/config.json.backup"), "w") as f:
            json.dump(config, f)

    except FileNotFoundError:
        print("No config file found, skipping backup")

def create_manifest_from_template(template_file: str, dummy_dataset) -> None:
    """Create a manifest file from a template file
    This procedure fills the manifest with the minimum required metadata to create a remote dataset

    Parameters
    ----------
    template_file : str
        Name of the template file in yaml format e.g. figshare.yaml
        the file is extracted from the templates folder
    """
    with open(f"./src/fairly/data/templates/{template_file}", "r") as f:
        template = f.read()
        template = yaml.safe_load(template)
        template['metadata']['title'] = "My fairly test"
        template['metadata']['description'] = "My test description"
        # Add files key to the manifest so that files are added to the dataset object
        template['files'] = { 'excludes': [], 'includes': ["*.txt"] }
        if template_file == "figshare.yaml":
            template['metadata']['authors'] = [ "John Doe" ]
        if template_file == "zenodo.yaml":
            template['metadata']['creators'] = [ { "name": "John Doe" } ]
            template['metadata']['authors'] = [ {"name" : "John Doe" } ]
            template['metadata']['description'] = "My test description"
            template['metadata']['license'] = 'cc-by-nc-4.0'
            template['metadata']['type'] = 'dataset'
            # template dates
            template['metadata']['publication_date'] = '2020-01-01'

    with open(f"{dummy_dataset}/manifest.yaml", "w") as f:
        f.write(yaml.dump(template))
 
# Set testing flag
fairly.TESTING = True

# Monkey patch the requests client library where we undo the patching of the HTTPConnection block size 
# that prevents us from using pytest-vcr to recort the requests
def _request(self, endpoint: str, method: str="GET", headers: dict=None, data=None, format: str=None, serialize: bool=True):
    """ Sends a HTTP request and returns the result

    Returns:
        Returned content and response

    """

    # Patch HTTPConnection block size to improve connection speed
    # ref: https://stackoverflow.com/questions/72977722/python-requests-post-very-slow
    # http.client.HTTPConnection.__init__.__defaults__ = tuple(
    #     x if x != 8192 else self.CHUNK_SIZE
    #     for x in http.client.HTTPConnection.__init__.__defaults__
    # )

    # Set default data format
    if not format:
        format = self.REQUEST_FORMAT

    # Serialize data if required
    if data is not None and serialize:
        if format == "json":
            data = json.dumps(data)

    # Create session if required
    if self._session is None:
        self._session = self._create_session()

    # Build URL address
    if not self.config["api_url"]:
        raise ValueError("No API URL address")

    # TODO: Better join of endpoint
    url = self.config["api_url"] + endpoint

    _headers = headers.copy() if headers else {}
    if format == "json":
        _headers["Accept"] = "application/json"
        if "Content-Type" not in _headers:
            _headers["Content-Type"] = "application/json"

    response = self._session.request(method, url, headers=_headers, data=data)
    response.raise_for_status()

    if response.content:
        if format == "json":
            content = response.json()
        else:
            content = response.content
    else:
        content = None

    return content, response
fairly.Client._request = _request

# Create a fairly config file for testing
setup_fairly_config_for_testing()
