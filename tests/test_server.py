import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from eye_hci.runtime import Runtime
from step6_hci import make_handler

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.patch=patch('eye_hci.runtime.PROFILE',Path(self.temp.name)/'default.json')
        self.patch.start()
        self.runtime=Runtime()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.runtime))
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
        self.port=self.server.server_port
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.worker.join();self.patch.stop();self.temp.cleanup()
    def request(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port)
        conn.request(method,path,body,headers or {})
        res=conn.getresponse();data=res.read();conn.close();return res.status,data
    def test_static_and_state(self):
        for path in ('/','/app.js','/style.css','/api/state'):
            status,data=self.request('GET',path);self.assertEqual(status,200);self.assertTrue(data)
        status,data=self.request('GET','/api/state');state=json.loads(data)
        self.assertFalse(state['real']);self.assertFalse(state['running'])
    def test_cross_origin_control_rejected(self):
        self.assertEqual(self.request('POST','/api/control','{"action":"pause"}')[0],403)
    def test_resume_blocked_until_ready(self):
        headers={'Origin':f'http://127.0.0.1:{self.port}','X-Eye-HCI':'1'}
        status,data=self.request('POST','/api/control','{"action":"resume"}',headers)
        self.assertEqual(status,400)
    def test_pause_and_stop(self):
        headers={'Origin':f'http://127.0.0.1:{self.port}','X-Eye-HCI':'1'}
        for action in ('pause','stop'):
            self.assertEqual(self.request('POST','/api/control',json.dumps({'action':action}),headers)[0],200)
    def test_wallpaper_success_and_fallback(self):
        with patch('eye_hci.desktop.wallpaper_image',return_value=b'fake-png'):
            self.assertEqual(self.request('GET','/api/wallpaper'),(200,b'fake-png'))
        with patch('eye_hci.desktop.wallpaper_image',side_effect=ValueError('Unavailable')):
            self.assertEqual(self.request('GET','/api/wallpaper')[0],404)
    def test_missing_camera_frame(self):
        self.assertEqual(self.request('GET','/api/frame')[0],204)

if __name__=='__main__':unittest.main()
