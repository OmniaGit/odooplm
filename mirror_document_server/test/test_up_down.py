'''
Created on Aug 30, 2019

@author: mboscolo
'''
import os
import unittest
import requests
from requests.auth import HTTPBasicAuth
auth = HTTPBasicAuth('OMNIA_USER', 'OMNIA_PASSWORD')


class Test(unittest.TestCase):

    def test1Upload(self):
        url = 'http://localhost:5000/upload_file'
        files = {'file': ('1250', open('test_up_down.py', 'rb'))}
        r = requests.post(url,
                          auth=auth,
                          files=files)
        assert r.status_code == 200

    def test2Download(self):
        new_file = '/tmp/down.py'
        if os.path.exists(new_file):
            os.remove(new_file)
        url = 'http://localhost:5000/download_file/1250'
        r = requests.get(url, auth=auth)
        r.raise_for_status()
        with open(new_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
        assert os.path.exists(new_file)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()