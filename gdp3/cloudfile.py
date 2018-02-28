#! /usr/bin/env python3

import os, sys
import json
import mimetypes
import logging

from .config import config
from .tokenfile import Token
from .utility import Gdp3Error

global DIRTYPE
global log, sApi

DIRTYPE = 'application/vnd.google-apps.folder';

log = logging.getLogger(__name__);
sApi = 'https://www.googleapis.com/drive/v3/files';

def writeToFile(res, sFile):
    if (config.isShowProgress):
        stream = sys.stdout;
    else:
        stream = open(os.devnull, 'w');
    with open(sFile, 'xb') as file:
        log.info('start downloading to file "{}"'.format(sFile));
        n = 1024**2;
        i = 1;
        bData = res.read(n);
        stream.write('\n');
        while bData:
            file.write(bData);
            stream.write('\r{} MB downloaded'.format(i));
            bData = res.read(n);
            i += 1;
        stream.write('\n');
        stream.flush();
        log.info('download completed');
        return sFile

class DirCheckError(Gdp3Error):
    def __init__(self, file):
        self.file = file;

class GetMetadataError(Gdp3Error):
    def __init__(self, file, res=None, sData=None):
        self.file = file;
        self.res = res;
        self.status = res.status if res else None;
        self.sData = sData;

class ListError(Gdp3Error):
    def __init__(self, file, res=None, sData=None):
        self.file = file;
        self.res = res;
        self.status = res.status if res else None;
        self.sData = sData;

class CloudFile():

    @property
    def sFileUrl(self):
        return '{}/{}'.format(self.sApi, self.sId);

    @property
    def sMime(self):
        return self.mMetadata.get('mimeType', '');
    @sMime.setter
    def sMime(self, value):
        self.mMetadata['mimeType'] = value;

    @property
    def sId(self):
        return self.mMetadata.get('id', '');
    @sId.setter
    def sId(self, value):
        self.mMetadata['id'] = value;

    @property
    def sName(self):
        return self.mMetadata.get('name', '');
    @sName.setter
    def sName(self, value):
        self.mMetadata['name'] = value;

    @property
    def aParents(self):
        return self.mMetadata.get('parents', []);
    @aParents.setter
    def aParents(self, value):
        self.mMetadata['parents'] = value;

    def __init__(self, sId=None, token=None, sTokenFile=None):
        global sApi
        self.mMetadata = {};
        self.sApi = sApi;
        self.sId = sId or '';
        #self.sFileUrl
        #self.sName
        #self.sMime
        #self.aParents
        if (not token):
            if (not sTokenFile):
                log.warning('token or sTokenFile should be given');
            else:
                token = Token(sTokenFile);
        self.token = token;
        if (not sId):
            log.warning('file ID not given');
    def __repr__(self):
        if (self.sName):
            return '<CloudFile "{}" - "{}">'.format(self.sName, self.sMime);
        else:
            return super().__repr__();
    def authCheck(self):
        return self.token and self.token.getAccessToken();
    def dirCheck(self):
        global DIRTYPE
        assert self.sId;
        if (not self.sMime):
            self.getMetadata();
        if (self.sMime == DIRTYPE):
            return self.sId;
        else:
            return False;
    def getMetadata(self, sFields=None, sExportMime=None, isRaise=True):
        global log
        if (isRaise is None):
            isRaise = True;
        if (not self.sId):
            log.error('can not get metadata without ID');
            if (isRaise):
                raise GetMetadataError(self);
            else:
                return False;
        if (not sFields):
            aFields = ('id', 'name', 'mimeType', 'parents', 'size', 'webContentLink', 'modifiedTime', 'createdTime');
            sFields = ','.join(aFields);
        mQuery = {
                'fields': sFields,
        };
        sUrl = self.sFileUrl;
        if (sExportMime):
            # export is not tested
            sUrl += '/export';
            mQuery['mimeType'] = sExportMime;
        res, sData = self.token.execute(sUrl, mQuery=mQuery);
        if (res.status == 200):
            mData = json.loads(sData);
            self.mMetadata.update(mData);
            log.debug('metadata got: {}'.format(mData));
            if ('parents' in aFields and not 'parents' in mData.keys()):
                log.debug('file "{}" have no parents'.format(self.sName));
                self.aParents = [];
            return mData;
        else:
            log.error('getting metadata status {}: {}'.format(res.status, sData));
            if (isRaise):
                raise GetMetadataError(self, res, sData);
            else:
                return False;
    def list(self, sFilter=None, sOrderBy='', sFields='', sPageToken='', isRaise=True):
        global log
        if (isRaise is None):
            isRaise is True;
        if (sFilter is None):
            sFilter = 'trashed = false';
            if (self.dirCheck()):
                sFilter += " and '{}' in parents".format(self.sId);
        if (not sOrderBy):
            sOrderBy = 'folder,createdTime,name';
        if (not sFields):
            aFields = ('id', 'name', 'mimeType', 'parents', 'size', 'webContentLink', 'modifiedTime', 'createdTime');
            sFields = ','.join(aFields);
            sFields = 'kind,nextPageToken,incompleteSearch,files({})'.format(sFields);
        mQuery = {};
        if (sFilter): mQuery['q'] = sFilter;
        if (sOrderBy): mQuery['orderBy'] = sOrderBy;
        if (sFields): mQuery['fields'] = sFields;
        if (sPageToken): mQuery['pageToken'] = sPageToken;
        mHeaders = {};
        sUrl = self.sApi;

        aFiles = []
        while True:
            if (sPageToken):
                mQuery['pageToken'] = sPageToken;
            res, sData =  self.token.execute(sUrl, mQuery=mQuery, mHeaders=mHeaders);
            if (res.status == 200):
                mData = json.loads(sData);
                #log.debug('list result: {}'.format(mData));
                aMetas = mData.get('files', []);
                for mMeta in aMetas:
                    file = CloudFile(mMeta['id'], self.token);
                    file.mMetadata.update(mMeta);
                    aFiles.append(file);
                sPageToken = mData.get('nextPageToken', '');
                if (sPageToken):
                    log.debug('pages remaining, continue ...'.format(sPageToken));
                else:
                    break;
            else:
                log.error('list status {}: {}'.format(res.status, sData));
                if (isRaise):
                    raise ListError(self, res, sData);
                else:
                    return False;
        return aFiles;

        res, sData =  self.token.execute(sUrl, mQuery=mQuery, mHeaders=mHeaders);
        if (res.status == 200):
            mData = json.loads(sData);
            #log.debug('list result: {}'.format(mData));
            sPageToken = mData.get('nextPageToken', '');
            if (sPageToken):
                log.warning('pages remaining, token: {}'.format(sPageToken));
            aMetas = mData.get('files', []);
            aFiles = []
            for mMeta in aMetas:
                file = CloudFile(mMeta['id'], self.token);
                file.mMetadata.update(mMeta);
                aFiles.append(file);
            return aFiles;
        else:
            log.error('list status {}: {}'.format(res.status, sData));
            if (isRaise):
                raise ListError(self, res, sData);
            else:
                return False;

    def create(self, sId='', sName='', sMimeType='', aParents=[], isKeep=False):
        global log
        sMethod = 'POST';
        sUrl = self.sApi;
        sMimeType = sMimeType or mimetypes.guess_type(sName)[0] or 'application/octet-stream';
        mQuery = {
                'keepRevisionForever': isKeep,
        }
        mMeta = {}
        if (sId): mMeta['id'] = sId;
        if (sName): mMeta['name'] = sName;
        if (sMimeType): mMeta['mimeType'] = sMimeType;
        if (aParents): mMeta['parents'] = aParents;
        bMeta = json.dumps(mMeta).encode('utf-8');
        mHeaders = {};
        mHeaders['Content-Type'] = 'application/json; charset=UTF-8';
        mHeaders['Content-Length'] = len(bMeta);
        res, sData = self.token.execute(sUrl, data=bMeta, mQuery=mQuery, mHeaders=mHeaders, sMethod=sMethod);
        if (res.status == 200):
            mData = json.loads(sData);
            sId = mData.get('id');
            sName = mData.get('name');
            file = CloudFile(sId, self.token);
            file.mMetadata.update(mData);
            log.debug('file "{}" with ID "{}" created'.format(sName, sId));
            return file;
        else:
            log.error('create status {}: {}'.format(res.status, sData));
            return False;
    def download(self, sOutPath=None, isAbuse=False, isForce=False, aRange=None, sExportMime=None):
        global log
        if (not self.sId):
            log.error('can not download file without ID');
            return False
        if (not sOutPath):
            sOutPath = self.sName;
        if (os.path.exists(sOutPath)):
            log.error('file already exists; set isForce to True to overwrite it');
            return False;
        mQuery = {
                'alt': 'media',
                #'acknowledgeAbuse': 'true',
        };
        if (isAbuse):
            mQuery['acknowledgeAbuse'] = 'true';
        sUrl = self.sFileUrl;
        if (sExportMime):
            # export is not tested
            sUrl += '/export';
            mQuery['mimeType'] = sExportMime;
        #Range: bytes=500-999
        mHeaders = {};
        if (aRange):
            mHeaders['Range'] = 'bytes={d}-{d}'.format(aRange[0], aRange[1]);
        res, _ = self.token.execute(sUrl, mQuery=mQuery, mHeaders=mHeaders, isStream=True);
        try:
            if (res.status == 200):
                writeToFile(res, sOutPath);
                log.info('file "{}" downloaded to "{}"'.format(self.sName, os.path.abspath(sOutPath)));
                return True;
            else:
                sData = _ or res.read().decode('utf-8');
                log.error('download failed: {}'.format(sData));
                return False;
        finally:
            res.close();
    def mkdir(self, sName='', aParents=None):
        global log
        global DIRTYPE
        if (aParents is None and self.dirCheck()):
            aParents = [self.sId]
        sMimeType = DIRTYPE;
        return self.create(sName=sName, sMimeType=sMimeType, aParents=aParents);
    def remove(self, isRecur=False):
        global log
        if (not self.sId):
            log.error('can not remove file without ID');
            return False;
        if (not isRecur and self.dirCheck()):
            log.error('can not remove directory while recursive not set, deleting failed');
            return False;
        else:
            sMethod = 'DELETE';
            sUrl = self.sFileUrl;
            res, sData = self.token.execute(sUrl, sMethod=sMethod);
            if (res.status == 204):
                log.info('status "{}", file "{}" with ID "{}" deleted'.format(res.status, self.sName, self.sId));
            else:
                log.warning('status "{}: {}'.format(res.status, sData));
            return True;
    def rmdir(self):
        global log
        if (self.dirCheck()):
            return self.remove(True);
        else:
            log.error('file is not directory, deleting failed');
            return False;
    def copy(self, sName='', sMimeType='', aParents=[], isKeep=False):
        global log
        if (not self.sId or self.dirCheck()):
            log.error('can only make copy of normal file');
            return False;
        sMethod = 'POST';
        sUrl = self.sFileUrl;
        sUrl += '/copy';
        sMimeType = sMimeType or mimetypes.guess_type(sName)[0] or 'application/octet-stream';
        mQuery = {
                'keepRevisionForever': isKeep,
        }
        mMeta = {}
        if (sName): mMeta['name'] = sName;
        if (sMimeType): mMeta['mimeType'] = sMimeType;
        if (aParents): mMeta['parents'] = aParents;
        bData = json.dumps(mMeta).encode('utf-8');
        mHeaders = {};
        mHeaders['Content-Type'] = 'application/json; charset=UTF-8';
        mHeaders['Content-Length'] = len(bData);
        res, sData = self.token.execute(sUrl, data=bData, mQuery=mQuery, mHeaders=mHeaders, sMethod=sMethod);
        if (res.status == 200):
            mData = json.loads(sData);
            file = CloudFile(mData['id'], self.token);
            file.mMetadata.update(mData);
            log.info('file "{}" copied to "{}" with ID "{}"'.foramt(self.sName, file.sName, file.sId));
            return file;
        else:
            log.error('status {}: {}'.format(res.status, sData));
    def update(self, aRemoveParents=None, aAddParents=None):
        global log
        if (not self.sId):
            log.error('can not update metadata without ID');
            return False;
        sMethod = 'PATCH';
        sUrl = self.sFileUrl;
        mQuery = {}
        if (aRemoveParents): mQuery['removeParents'] = ','.join(aRemoveParents);
        if (aAddParents): mQuery['addParents'] = ','.join(aAddParents);
        aFields = ('modifiedTime', 'appProperties', 'description', 'mimeType', 'name', 'properties', 'starred', 'trashed');
        mMeta = {key: value for (key, value) in self.mMetadata.items() if key in aFields};
        mQuery['fields'] = ','.join(mMeta.keys());
        bData = json.dumps(mMeta).encode('utf-8');
        mHeaders = {};
        mHeaders['Content-Type'] = 'application/json; charset=UTF-8';
        mHeaders['Content-Length'] = len(bData);
        res, sData = self.token.execute(sUrl, data=bData, mQuery=mQuery, mHeaders=mHeaders, sMethod=sMethod);
        if (res.status == 200):
            mData = json.loads(sData);
            log.info('metadate updated: {}'.format(mData));
            self.getMetadata(isRaise=False);
            return True;
        else:
            log.error('status {}: {}'.format(res.status, sData));
            return False;
    def move(self, dirFile):
        global log
        sDirId = dirFile.dirCheck();
        if (sDirId):
            aOldDir = self.aParents;
            aNewDir = [sDirId];
            self.update(aOldDir, aNewDir);
        else:
            log.error('target is not a directory');
    def getChildren(self, sName=None, isPrefix=False):
        # WARNING: there are cases where client can not use "name = '<filename>'" to fetch the file desired even though <filename> is exactly equal to name of the desired file;
        # using 'contains' instead of '=' (that is, "name contains '<filename>'") might be a workaround
        if (not self.dirCheck()):
            return False;
        else:
            if (sName):
                sOperator = 'contains' if isPrefix else '=';
                sFilter = "name {} '{}' and '{}' in parents and trashed = false".format(sOperator, sName, self.sId);
            else:
                sFilter = "'{}' in parents and trashed = false".format(self.sId);
            aFiles = self.list(sFilter);
            if (aFiles is not False):
                return aFiles;
            else:
                return False;
    def getDirChildren(self, sName=None, isPrefix=False):
        global DIRTYPE;
        if (not self.dirCheck()):
            return False;
        else:
            if (sName):
                sOperator = 'contains' if isPrefix else '=';
                sFilter = "name {} '{}' and '{}' in parents and mimeType = '{}' and trashed = false".format(sOperator, sName, self.sId, DIRTYPE);
            else:
                sFilter = "'{}' in parents and mimeType = '{}' and trashed = false".format(self.sId, DIRTYPE);
            aFiles = self.list(sFilter);
            if (aFiles is not False):
                return aFiles;
            else:
                return False;
    def trash(self):
        global log
        if (self.mMetadata.get('trashed') == True):
            log.warning('file already in trash');
        else:
            self.mMetadata['trashed'] = True;
            isDone = self.update(self);
            if (isDone):
                log.info('file trashed');
                return True
    def untrash(self):
        global log
        if (self.mMetadata.get('trashed') == False):
            log.warning('file not in trash');
        else:
            self.mMetadata['trashed'] = False;
            isDone = self.update(self);
            if (isDone):
                log.info('file untrashed');
                return True
