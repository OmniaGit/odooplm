# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solution
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''
Created on Aug 30, 2019

@author: mboscolo
'''
import json
import os
import hashlib
from app import app
from flask import Flask, flash, request, redirect, send_from_directory, make_response, jsonify
from werkzeug.utils import secure_filename
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()


@app.route('/upload_file', methods=['POST'])
@auth.login_required
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file_file = request.files['file']
        if file_file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)
        if file_file:
            filename = secure_filename(file_file.filename)
            file_file.save(getNewFileName(filename))
            flash('File successfully uploaded')
            data = {'message': 'Created', 'code': 'SUCCESS'}
            return make_response(jsonify(data), 200)
        else:
            return redirect(request.url)


@app.route('/download_file/<path:doc_id>', methods=['GET', 'POST'])
@auth.login_required
def download(doc_id):
    filename = getNewFileName(doc_id)
    return send_from_directory(directory=os.path.dirname(filename), filename=os.path.basename(filename))


@app.route('/document_is_there/<path:doc_id>', methods=['GET'])
@auth.login_required
def document_is_there(doc_id):
    file_name = getNewFileName(doc_id)
    path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    return json.dumps(os.path.exists(path))


@auth.verify_password
def verify_password(username, password):
    return app.config['USER_NAME'] == username and app.config['PASSWORD'] == password


# def md5(fname):
#     hash_md5 = hashlib.md5()
#     with open(fname, "rb") as f:
#         for chunk in iter(lambda: f.read(4096), b""):
#             hash_md5.update(chunk)
#     return hash_md5.hexdigest()

# @app.route('/md5_file', methods=['GET'])
# @auth.login_required
# def check():
#     file_name = request.args.get('filename')
#     path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
#     if os.path.exists(path):
#         return md5(path) == request.args.get('md5')
#     return False

def getNewFileName(doc_id):
    base_path = app.config['UPLOAD_FOLDER']
    folder_name = "ir_%s" % ("0" if not doc_id[:-3] else doc_id[:-3])
    file_name = "doc_%s" % doc_id
    base_path = os.path.join(base_path, folder_name)
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    return os.path.join(base_path, file_name)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
