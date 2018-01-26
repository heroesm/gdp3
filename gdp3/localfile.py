#! /usr/bin/env python3

import sys, os
import urllib.request
import urllib.parse
import json
import re
import time
import mimetypes
import logging

from .config import config
from .tokenfile import Token

global log
global sHome
global FILENAME
global TOKENFILE

log = logging.getLogger(__name__);
sHome = config.sHome;
FILENAME = '';
TOKENFILE = 'token1.json';

sApi = 'https://www.googleapis.com/upload/drive/v3/files';
sUploadType = 'resumable';

def loadFromFile(sFile=None, nCursor=None):
    # split file data to avoid large memory consumption and to display upload process
    global log
    if (not sFile): sFile;
    if (not nCursor): nCursor;
    if (config.isShowProgress):
        stream = sys.stdout;
    else:
        stream = open(os.devnull, 'w');
    with open(sFile, 'rb') as file:
        file.seek(nCursor);
        log.debug('reading from bytes {} in file {}'.format(file.tell(), sFile));
        stream.write('\n');
        n = 1024**2;
        i = 1;
        bData = file.read(n);
        while (bData):
            yield bData
            stream.write('\r{} MB processed'.format(i));
            bData = file.read(n);
            i += 1;
    stream.write('\n');
    stream.flush();

class File():
    sApi = 'https://www.googleapis.com/upload/drive/v3/files';
    sUploadType = 'resumable';
    PRE = 0;
    INIT = 1;
    PARTIAL = 2;
    DONE = 3;
    ERROR = 4;
    mStatus = {
            0: 'prepared',
            1: 'initialised',
            2: 'partial uploaded',
            3: 'upload completed',
            4: 'error condition'
    }

    def __init__(self, sFile, token=None, sTokenFile=None, mMeta=None, sName=None, sMime=None):
        global log
        if (not os.path.exists(sFile)):
            raise FileNotFoundError('the file to be uploaded "{}" does not exist'
                    .format(sFile)
            )
        self.sFile = sFile;
        log.debug('file to be uploaded: {}'.format(sFile));
        self.mMeta = mMeta or {};
        if (sName):
            mMeta['name'] = str(sName);
        if (not sMime):
            sMime = mimetypes.guess_type(sFile)[0];
            if (not sMime):
                sMime = 'application/octet-stream';
        log.debug('MIME is set to {}'.format(sMime));
        self.sMime = sMime;
        self.nFileSize = os.path.getsize(sFile);
        if (not token):
            if (not sTokenFile):
                log.warning('token or sTokenFile should be given for uploading to succeed');
            else:
                token = Token(sTokenFile);
        self.token = token;
        self.sSessionUrl = None;
        self.nStatus = self.PRE;
        self.nCursor = 0;
        self.nError = None;
        self.nBirth = 0;
        self.sId = None;
    def __repr__(self):
        return '<File "{}">'.format(self.sFile);
    def shift(self, nNew):
        global log
        log.debug('shift from status "{}" to "{}"'.format(self.mStatus[self.nStatus], self.mStatus[nNew]));
        self.nStatus = nNew;
        if (nNew == self.PRE):
            self.nCursor = 0;
        elif (nNew == self.INIT):
            self.nCursor = 0;
            self.saveSession();
        elif (nNew == self.PARTIAL):
            self.saveSession();
        elif (nNew == self.DONE):
            log.debug('{} uploaded'.format(self));
            self.clearSession();
        elif (nNew == self.ERROR):
            log.error('encouter HTTP error code: {}'.format(self.nError));
            self.saveSession();
    def saveSession(self, sSessionFile=None):
        global log
        if (not sSessionFile):
            sSessionFile = config.sSessionFile;
        log.debug('save upload session to file {}'.format(sSessionFile));
        sOut = '{}\n{}\n{}\n'.format(self.nBirth, self.sFile, self.sSessionUrl);
        with open(sSessionFile, 'wb') as f:
            f.write(sOut.encode('utf-8'));
    def loadSession(self, sSessionFile=None):
        global log
        if (not sSessionFile):
            sSessionFile = config.sSessionFile;
        if (not os.path.isfile(sSessionFile)):
            log.debug('upload session file nonexistent, loading abort');
            return False
        log.debug('load upload session from file {}'.format(sSessionFile));
        with open(sSessionFile, 'rb') as file:
            aData = file.readlines();
        try:
            sTime, sFile, sUrl = [x.strip().decode('utf-8') for x in aData];
            nTime = int(sTime);
        except Exception as e:
            log.exception('loading aborted');
            return False
        else:
            if (nTime >= self.nBirth and sFile == self.sFile):
                self.nBirth = nTime;
                self.sSessionUrl = sUrl;
                nStatus = self.queryStatus();
                log.debug('status: {}\nsession url renewed to {}'.format(nStatus, sUrl));
                return True
            else:
                log.debug('inconsistent session, loading abort');
                try:
                    os.remove(sSessionFile);
                except FileNotFoundError as e:
                    pass
                return False
    def clearSession(self, sSessionFile=None):
        if (not sSessionFile):
            sSessionFile = config.sSessionFile;
        if (os.path.exists(sSessionFile)):
            try:
                os.remove(sSessionFile);
            except FileNotFoundError as e:
                pass
            else:
                log.debug('session file "{}" removed'.format(sSessionFile));
    def queryStatus(self):
        global log
        sUrl = self.sSessionUrl;
        sMethod = 'PUT';
        nSize = self.nFileSize;
        mHeaders = {
                'Content-Range': 'bytes */{}'.format(nSize),
        };
        res, sData = self.token.execute(sUrl, mHeaders=mHeaders, sMethod=sMethod);
        nStatus = res.status;
        log.debug('query result:\n  status: {}\n  response: {}'.format(nStatus, sData));
        if (nStatus in [200, 201]):
            mData = json.loads(sData);
            self.sId = mData.get('id');
            self.shift(self.DONE);
        elif (nStatus == 308):
            sRange = res.getheader('Range')
            log.debug('uploaded: {}'.format(sRange));
            if (sRange):
                match = re.search(r'bytes=0-(\d+)', sRange);
                self.nCursor = int(match.group(1)) + 1;
                log.debug('cursor reset to interrupted bytes {}'.format(self.nCursor));
            self.shift(self.PARTIAL);
        if (nStatus == 404):
            log.warning('upload session expired, restarting...');
            self.shift(self.PRE);
        return nStatus
    def initSession(self, sMethod=None, sFileId=None, mMeta=None):
        global log
        log.debug('initialise a new upload session');
        if (not sMethod): sMethod = 'POST';
        if (not mMeta): mMeta={};
        mMeta.update(self.mMeta);
        if (not mMeta.get('name')):
            mMeta['name'] = os.path.basename(self.sFile);
        sMime = self.sMime;
        nSize = self.nFileSize;
        mQuery = {
                'uploadType': 'resumable'
        };
        sQuery = urllib.parse.urlencode(mQuery, True);
        sUrl = sApi;
        if (sFileId):
            sUrl += '/' + str(sFileId);
            sMethod = 'PUT';
        sUrl += '?' + sQuery;
        mHeaders = {
                'X-Upload-Content-Type': sMime,
                'X-Upload-Content-Length': nSize,
                'Content-Length': 0
        };
        if (mMeta):
            bMeta = json.dumps(mMeta).encode('utf-8');
            mHeaders['Content-Type'] = 'application/json; charset=UTF-8';
            mHeaders['Content-Length'] = len(bMeta);
        else:
            bMeta = b'';
        log.debug('metadata to be sent: {}'.format(bMeta));
        res, sData = self.token.execute(sUrl, data=bMeta, mHeaders=mHeaders, sMethod=sMethod);
        assert res.status == 200
        if (res.status == 200):
            self.sSessionUrl = res.getheader('Location');
            self.nBirth = int(time.time());
            log.debug('upload session URI: ' + self.sSessionUrl);
            self.shift(self.INIT);
            return True
        else:
            log.error('status {}: {}'.format(res.status, sData));
            return False
    def upload(self, sUrl=None):
        global log
        if (self.nStatus == self.DONE):
            log.debug('upload already completed');
            return self.sId if self.sId else True
        if (not sUrl): sUrl = self.sSessionUrl;
        sMethod = 'PUT';
        nLength = nSize = self.nFileSize;
        iData = loadFromFile(self.sFile, self.nCursor);
        mHeaders = {};
        if (self.nCursor):
            # do resume
            log.debug('resuming upload...');
            sRange = 'bytes {}-{}/{}'.format(self.nCursor, nSize - 1, nSize);
            nLength = nSize - self.nCursor;
            mHeaders['Content-Range'] = sRange;
        mHeaders['Content-Length'] = nLength;
        res, sData = self.token.execute(sUrl, data=iData, mHeaders=mHeaders, sMethod=sMethod)
        log.debug('response: {}'.format(sData));
        #log.debug('response headers: {}'.format(res.getheaders()));
        if (res.status in [200, 201]):
            mData = json.loads(sData);
            self.sId = mData.get('id');
            self.shift(self.DONE);
            return self.sId if self.sId else True
        elif (res.status in [500, 502, 503, 504]):
            self.nError = res.status;
            self.shift(self.ERROR);
            time.sleep(3);
            nStatus = self.queryStatus();
            log.error('get status {} from query'.format(nStatus));
            if (self.nStatus == self.PARTIAL):
                isDone = self.upload();
                return isDone;
            else:
                return False
        else:
            self.nError = res.status;
            log.error('status {}: {}'.format(res.status, sData));
            self.shift(self.ERROR);
            return False

def uploadFile(sPath=None, token=None, sToken=None):
    global TOKENFILE;
    if (not token):
        if (not sToken):
            sToken = TOKENFILE;
        token = Token(sToken);
    assert token;
    #sPath = os.path.join(sHome, sPath);
    if (not sPath):
        if (__name__ == '__main__' and sys.argv[1:2]):
            sPath = sys.argv[1];
        else:
            sPath = FILENAME;
    file = File(sPath, token);
    if (not file.loadSession()):
        file.initSession();
    sId = file.upload();
    log.info('upload completed, file ID: "{}"'.format(sId));
    return sId

def test():
    uploadFile();

def main():
    test();

if __name__ == '__main__':
    main();
