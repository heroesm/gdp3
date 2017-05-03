#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

from pprint import pprint
import re
import os
from wsgiref.simple_server import make_server
import threading
import os.path

from ..config import config

global nWsgiPort
global isCodeFetched

isCodeFetched = False
nWsgiPort = config.nWsgiPort;

def runServer(isNonce=None, sCodeFile=None):

    def application(env, start_response):
        global isCodeFetched
        nonlocal isNonce, sCodeFile
        nonlocal server
        sRequestFile = os.path.join(config.sDataDir, 'request');
        with open(sRequestFile, 'w') as file:
            pprint(env, file);
        start_response('200 OK', [('Content-Type','text/plain')])
        if ('oauth' in env['PATH_INFO']):
            yield b'oauth process\n';
            sQuery = env['QUERY_STRING'];
            match = re.search(r'code=([^&]+)', sQuery, re.I);
            if (match and match.group(1)):
                print(sQuery);
                sCode = match.group(1).strip();
                with open(sCodeFile, 'wb') as file:
                    file.write(sCode.encode('utf-8'));
                with open(config.sCodeLog, 'a') as file:
                    file.write(env['QUERY_STRING']);
                    file.write('\n\n')
                yield b'get application code\n';
                isCodeFetched = True;
            else:
                yield b'denied\n';
            if (isNonce):
                threading.Thread(target=server.shutdown).start();
        yield b'\nended';

    global nWsgiPort
    if (not sCodeFile): sCodeFile = config.sCodeFile;
    try:
        server = make_server('', nWsgiPort, application);
        print('wsgi oauth server established on port {}'.format(nWsgiPort));
        server.serve_forever();
    finally:
        if ('server' in locals()): server.server_close()

def main():
    runServer();

if __name__ == '__main__':
    main();
