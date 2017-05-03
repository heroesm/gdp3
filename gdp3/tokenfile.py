#! /usr/bin/env python3

import json
import time
import urllib.request
import urllib.parse
import urllib.error
from os.path import exists, join
import logging

from .config import config

global log

log = logging.getLogger(__name__);

def mergeQuery(sUrl, mQuery):
    parts = urllib.parse.urlsplit(sUrl);
    scheme, netloc, path, query, fragment = parts;
    mQueryNew = urllib.parse.parse_qs(query);
    mQueryNew.update(mQuery);
    query = urllib.parse.urlencode(mQueryNew, doseq=True);
    parts = scheme, netloc, path, query, fragment;
    sUrl = urllib.parse.urlunsplit(parts);
    return sUrl

class Token():
    mLoadMap = {
            'access_token': 'sAccess',
            'expires_in': 'nLife',
            'refresh_token': 'sRefresh',
            'token_type': 'sType',
            'nBirth': 'nBirth',
            'client_id': 'sId',
            'client_secret': 'sSecret',
            'sClientType': 'sClientType'
    }
    @property
    def mSaveMap(self):
        return {value: key for (key, value) in self.mLoadMap.items()};

    def __init__(self, sTokenFile=None, sClientFile=None, sType=None, sAccess=None, sRefresh=None, nBirth=None, nLife=None, sId=None, sSecret=None, sClientType=None):
        self.sType = 'Bearer';
        self.sAccess = '';
        self.sRefresh = '';
        self.nBirth = 0;
        self.nLife = 0;
        self.sId = '';
        self.sSecret = '';
        self.sClientType = '';
        self.sDeath = '';
        self.sTokenFile = '';
        if (sTokenFile):
            if (not exists(sTokenFile)):
                sTokenFile = join(config.sDataDir, sTokenFile);
            self.loadFromJson(sTokenFile);
        if (sClientFile):
            self.loadClientJson(sClientFile);
        mData = locals().copy()
        mData = self.sanitise(mData);
        self.__dict__.update(mData);
        if (self.nLife): self.sDeath = time.ctime(self.nBirth + self.nLife);
    def checkExpire(self):
        global log
        isExpire = True if time.time() > self.nBirth + self.nLife else False;
        if (isExpire):
            log.debug('access token expired');
        return isExpire;
    def refreshToken(self):
        global log
        sUrl = 'https://www.googleapis.com/oauth2/v4/token';
        mData = {
                'refresh_token': self.sRefresh,
                'client_id': self.sId,
                'client_secret': self.sSecret,
                'grant_type': 'refresh_token'
        }
        bData = urllib.parse.urlencode(mData, True).encode('utf-8');
        try:
            res = urllib.request.urlopen(sUrl, bData);
        except urllib.error.HTTPError as e:
            log.error('can\'t refresh access token due to:\n{}'.format(e));
            errRes = getattr(e, 'fp', None);
            if (errRes):
                log.error(errRes.read().decode('utf-8'));
        else:
            bData = res.read();
            res.close();
            mData = json.loads(bData.decode('utf-8'));
            self.sAccess = mData['access_token'];
            self.nLife = mData['expires_in'];
            self.sType = mData['token_type'];
            self.nBirth = int(time.time());
            self.sDeath = time.ctime(self.nBirth + self.nLife);
            log.debug('access token refreshed: {}'.format(self.sAccess));
            if (self.sTokenFile):
                self.saveToJson(self.sTokenFile);
            return True
    def revokeToken(self):
        global log
        sUrl = 'https://accounts.google.com/o/oauth2/revoke';
        sArg = 'token={}'.format(urllib.parse.quote(self.sRefresh));
        sUrl = '{}?{}'.format(sUrl, sArg);
        mHeaders = {'Content-type': 'application/x-www-form-urlencoded'}
        req = urllib.request.Request(sUrl, data=b'', headers=mHeaders);
        try:
            res = urllib.request.urlopen(req);
        except urllib.error.HTTPError as e:
            log.error('can\'t revoke access token due to:\n{}'.format(e));
            errRes = getattr(e, 'fp', None);
            if (errRes):
                log.error(errRes.read().decode('utf-8'));
        else:
            sData = res.read().decode('utf-8');
            res.close();
            self.sAccess = self.sRefresh = None;
            log.info('token revoked:\n{}'.format(sData));
            return True
    def getAccessToken(self):
        global log
        isValid = True;
        if (not self.sAccess or self.checkExpire()):
            isValid = self.refreshToken();
        if (isValid):
            return self.sAccess;
        else:
            log.error('can\'t get valid access token')
            return None
    def saveToJson(self, sFile):
        global log
        assert self.sAccess or self.sRefresh;
        try:
            mOut = self.__dict__.copy();
            mOut = {
                    self.mSaveMap[key]: value
                    for (key, value) in mOut.items()
                    if key in self.mSaveMap
            }
            #log.debug('token info saved:\n{}'.format(mOut))
            bData = json.dumps(mOut).encode('utf-8');
            file = open(sFile, 'wb');
            file.write(bData);
        except Exception as e:
            #log.error('fail to export:\n{}'.format(e));
            log.exception('fail to export');
        else:
            log.debug('token info saved to "{}"'.format(sFile));
            return True
        finally:
            if('file' in locals()): file.close();
    @staticmethod
    def sanitise(mIn):
        mOut = {}
        key = 'sType';
        if (isinstance(mIn.get(key), str)): mOut[key] = mIn[key];
        key = 'sAccess';
        if (isinstance(mIn.get(key), str)): mOut[key] = mIn[key];
        key = 'sRefresh';
        if (isinstance(mIn.get(key), str)): mOut[key] = mIn[key];
        key = 'nLife';
        if (isinstance(mIn.get(key), int)): mOut[key] = mIn[key];
        key = 'nBirth';
        if (isinstance(mIn.get(key), int)): mOut[key] = mIn[key];
        key = 'sId';
        if (isinstance(mIn.get(key), str)): mOut[key] = mIn[key];
        key = 'sSecret';
        if (isinstance(mIn.get(key), str)): mOut[key] = mIn[key];
        key = 'sClientType';
        if (isinstance(mIn.get(key), str)): mOut[key] = mIn[key];
        key = 'sTokenFile';
        if (isinstance(mIn.get(key), str)): mOut[key] = mIn[key];
        return mOut;
    def loadFromJson(self, sFile):
        global log
        try:
            #if (not exists(sFile)):
            #        sFile = join(config.sDataDir, sFile);
            file = open(sFile, 'rb');
            sData = file.read().decode('utf-8');
            mIn = json.loads(sData);
            mIn = {
                    self.mLoadMap[key]: value
                    for (key, value) in mIn.items()
                    if key in self.mLoadMap
            }
            #log.debug('token info loaded:\n{}'.format(mIn));
        except FileNotFoundError as e:
            log.error('can not find file "{}"'.format(sFile));
            raise;
        except json.JSONDecodeError as e:
            log.error('mistaken JSON file');
        else:
            mIn = self.sanitise(mIn);
            self.__dict__.update(mIn);
            log.debug('token info loaded from "{}"'.format(sFile));
            return True
        finally:
            if('file' in locals()): file.close();
    def loadClientJson(self, sFile):
        global log
        try:
            if (not exists(sFile)):
                    sFile = join(config.sDataDir, sFile);
            file = open(sFile, 'rb');
            sData = file.read().decode('utf-8');
            mIn = json.loads(sData);
            sClientType, mIn = list(mIn.items())[0];
            mIn = {
                    'sClientType': sClientType,
                    'sId': mIn['client_id'],
                    'sSecret': mIn['client_secret']
            }
            #log.debug('client info loaded:\n{}'.format(mIn));
        except FileNotFoundError as e:
            log.error('can not find file "{}"'.format(sFile));
        except json.JSONDecodeError as e:
            log.error('mistaken JSON file');
        else:
            mIn = self.sanitise(mIn);
            self.__dict__.update(mIn);
            log.info('loaded from "{}"'.format(sFile));
            return True
        finally:
            if('file' in locals()): file.close();

    def execute(self, sUrl, data=None, mQuery=None, mHeaders=None, sMethod=None):
        # sUrl can contain partial arguments (?)
        # data shall be bytes or iterable
        global log
        global mergeQuery
        assert sUrl
        if (not mQuery): mQuery = {};
        if (not mHeaders): mHeaders = {};
        if (not sMethod and data is None):
            sMethod = 'GET';
        sToken = self.getAccessToken();
        if (not sToken):
            log.error('no access token available, execution aborted');
            return None
        sUrl = mergeQuery(sUrl, mQuery);
        mHeaders.update({
                'Authorization': '{} {}'.format(self.sType, sToken)
        });
        req = urllib.request.Request(sUrl, data=data, headers=mHeaders, method=sMethod);
        log.debug('"{}" to "{}"'.format(req.get_method(), req.full_url));
        try:
            res = urllib.request.urlopen(req, timeout=20);
        except urllib.error.HTTPError as e:
            log.error('request failed due to: {}'.format(e));
            errRes = getattr(e, 'fp', None);
            if (errRes):
                sData = errRes.read().decode('utf-8');
                sData and log.error(sData);
                return errRes
        else:
            #sRes = res.read().decode('utf-8');
            #log.debug(sRes)
            #res.close()
            return res;
