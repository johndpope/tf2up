"""Simple wrapper to upgrade the files by github URL"""

import json
import os
import urllib

import requests

from hashlib import md5
from flask import Flask, redirect, request
app = Flask(__name__)

NBDIME_URL = "http://localhost:81/d/"
# NBDIME_URL = "http://127.0.0.1:64533/d/"

def download_file(requested_url: str) -> str:
    """Download a file from github repository"""

    url = f"https://github.com/{requested_url.replace('blob', 'raw')}"
    resp = requests.get(url)
    print(requested_url)
    print(resp.status_code)

    if resp.status_code != 200:
        raise ValueError

    return resp.text


def convert_file(in_file, out_file):
    comand = f"tf_upgrade_v2 --infile {in_file} --outfile {out_file}"

    import subprocess

    p = subprocess.Popen(comand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = p.stdout.readlines()
    p.wait()

    print(result)

# TODO: return url
def process_file(requested_url: str, force=False):

    _, file_ext = os.path.splitext(requested_url)
    folder_hash = md5(requested_url.encode('utf-8')).hexdigest()

    path = f"/notebooks/{folder_hash}"
    original = f"original{file_ext}"
    converted = f"converted{file_ext}"

    if not os.path.exists(path):
        file_content = download_file(requested_url)

        os.mkdir(path)
        with open(f"{path}/{original}", "w") as original_file:
            original_file.write(file_content)

        # TODO: try to convert


        convert_file(f"{path}/{original}", f"{path}/{converted}")

    return path, (original, converted)



@app.route("/")
def hello():
    return "Hello World!"


@app.route("/d/<path:path>", methods=['GET'])
def proxy(path):
    """Proxy request on python side"""
    additional_params = '&'.join([f"{k}={v}" for k,v in request.values.items()])
    url = f"{NBDIME_URL}{path}?{additional_params}"

    print(f"URL: {url}")

    try:
        response = urllib.request.urlopen(url)
        return response.read()
    except urllib.error.URLError:
        return "Something went wrong, can not proxy"


@app.route("/d/<path:path>", methods=['POST'])
def proxy_api(path):
    """Proxy request on python side"""
    url = f"{NBDIME_URL}{path}"

    try:
        payload = json.dumps(request.json).encode()
        req =  urllib.request.Request(url, data=payload, headers={'content-type': 'application/json'}) # this will make the method "POST"
        resp = urllib.request.urlopen(req)

        return resp.read()
    except urllib.error.URLError:
        return "Something went wrong, can not proxy"

# TODO force refresh
@app.route('/<path:path>')
def catch_all(path):

    # TODO: proper status codes
    if not (path.endswith('.py') or path.endswith('.ipynb')):
        return "Currently we only support `.py` and `.ipynb` files."

    try:
        folder, files = process_file(path)

        url = f"/d/diff?base={folder}/{files[0]}&remote={folder}/{files[1]}"
        print(url)
        return redirect(url, code=302)

    except ValueError:
        return "Can not download the file :( . Are you sure the url is correct?"



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")