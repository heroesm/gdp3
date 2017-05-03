#! /usr/bin/env python3

import os,sys
from pprint import pprint
import os.path
import logging

from .tokenfile import Token
from .oauth import oauthwsgi
from .oauth import auth
from .oauth import exchange
from .config import config

global log

log = logging.getLogger(__name__);

def prepareDir():
    global sHome
    global sDir
    # cd to the directory of running script
    sPath = sys.argv[0] if __name__ == '__main__' else __file__;
    sDir = os.path.split(sPath)[0];
    if (sDir): os.chdir(sDir);
    sHome = os.path.expanduser('~');

def batchSave(sName, token):
    i = 1;
    sPath = os.path.join(config.sDataDir, '{}{}.json'.format(sName, i));
    while (os.path.exists(sPath)):
        i += 1
        sPath = os.path.join(config.sDataDir, '{}{}.json'.format(sName, i));
    token.saveToJson(sPath);

def reAuth(sClientFile=None, sCodeFile=None, sTokenFile=None):
    global log
    if (not sClientFile):
        sClientFile = config.sClientFile;
    if (not sCodeFile):
        sCodeFile = config.sCodeFile;
    if (not sTokenFile):
        sTokenFile = config.sTokenFile;
    log.info('using client credential to get application code');
    auth.auth(sClientFile);
    log.info('starting wsgi server to receive redirection response');
    oauthwsgi.runServer(isNonce=True, sCodeFile=sCodeFile);
    log.info("wsgi server stopped");
    assert (oauthwsgi.isCodeFetched);
    log.info("using application code to get access and refreshing token");
    mToken = exchange.exchangeForToken(sClientFile, sCodeFile, sTokenFile)
    token = Token(sTokenFile, sClientFile);
    log.debug(vars(token))
    sName = 'token';
    batchSave(sName, token);
    sName = 'refresh_token' if ('refresh_token' in mToken) else 'access_token';
    batchSave(sName, token);
    return token

def test():
    token = reAuth();
    res = token.execute('https://www.googleapis.com/drive/v3/about?fields=user');
    pprint(res.read().decode());
    return token

def main():
    test();

if __name__ == '__main__':
    main();
