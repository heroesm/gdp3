#! /usr/bin/env python3

import urllib.request
import urllib.parse
import urllib.error
import os
import os.path
import json
import time
from pprint import pprint
import logging

from ..config import config


global sRedirect
global log

log = logging.getLogger(__name__);
sRedirect = config.sRedirect;

def exchangeForToken(sClientFile=None, sCodeFile=None, sSaveTo=None, *, sCode=None, sId=None, sSecret=None):
    def extractData():
        global log
        nonlocal sClientFile, sCodeFile, sSaveTo, sCode, sId, sSecret
        if (not (sId and sSecret)):
            if (not sClientFile):
                sClientFile = config.sClientFile;
            log.debug('load client info from file "{}"'.format(sClientFile));
            with open(sClientFile, 'r') as file:
                sData = file.read();
            m1 = json.loads(sData);
            m1 = m1[config.sClientType];
            sId = m1['client_id'];
            sSecret = m1['client_secret'];
        log.debug('client ID: {}\nclient secret: {}'.format(sId, sSecret));
        if (not sCode):
            if (not sCodeFile):
                sCodeFile = config.sCodeFile;
            with open(sCodeFile) as file:
                sData = file.read();
            sCode = sData.strip();
            log.debug('load application code: {}'.format(sCode));
        mData = {
            'code': sCode,
            'client_id': sId,
            'client_secret': sSecret,
            'redirect_uri': sRedirect,
            'grant_type': 'authorization_code',
        };
        bData = urllib.parse.urlencode(mData).encode();
        return bData;

    def handleToken(mToken):
        global log
        nonlocal sSaveTo
        if (not sSaveTo): sSaveTo = config.sTokenFile;
        mToken['nBirth'] = int(time.time());
        if ('refresh_token' in mToken.keys()):
            with open(os.path.join(config.sDataDir, 'refresh_token'), 'wb') as file:
                file.write(mToken['refresh_token'].encode('utf-8'));
        sToken = json.dumps(mToken);
        with open(sSaveTo, 'wb') as file:
            file.write(sToken.encode('utf-8'));
        with open(config.sTokenLog, 'a') as file:
            pprint(mToken, file);
            file.write('\n\n\n');

    def requestToken():
        global log
        sUrl = 'https://www.googleapis.com/oauth2/v4/token';
        log.debug('post to URL: {}'.format(sUrl))
        bData = extractData();
        request1 = urllib.request.Request(sUrl, data=bData);
        log.debug('post data: {}'.format(request1.data));
        try:
            res = urllib.request.urlopen(request1, timeout=20);
        except urllib.error.HTTPError as e:
            log.error('can\'t exchange for token due to:\n{}'.format(e));
            errRes = getattr(e, 'file', None);
            if (errRes):
                log.error(errRes.read().decode('utf-8'));
        else:
            sData = res.read().decode('utf-8');
            mToken = json.loads(sData);
            log.debug(mToken);
            handleToken(mToken);
            return mToken;
        finally:
            if ('res' in locals()): res.close();

    mToken = requestToken();
    return mToken;

def main():
    exchangeForToken();

if __name__ == '__main__':
    main();
