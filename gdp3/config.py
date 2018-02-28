import sys
import os
from os.path import split, join, exists
import logging

# constants to be modified
ISWEB = False;
SCHEME = 'http';
HOST = '';
PORT = 8080;
DATADIR = 'data';
LOGLEVEL = logging.DEBUG;
CLIENT = 'client_secret.json'
WEBCLIENT = 'web_client_secret.json'
RETRYCOUNT = 5;
SHOWPROGRESS = True;

# variables for reference, normally not used
sApi = 'https://www.googleapis.com/drive/v3/';
sFileApi = 'https://www.googleapis.com/drive/v3/files';
sUploadApi = 'https://www.googleapis.com/upload/drive/v3/files';
sFolderMime = 'application/vnd.google-apps.folder';

class Config():
    # all the configuration variables
    isWeb = ISWEB;
    sHome = os.path.expanduser('~');
    sDir = split(__file__)[0];
    nWsgiPort = PORT;
    sRedirect = '';
    sDataDir = join(sDir, DATADIR);
    sCodeFile = join(sDataDir, 'code');
    sCodeLog = '';
    sTokenFile = join(sDataDir, 'token');
    sTokenLog = '';
    sClientType = '';
    sClientFile = '';
    sSessionFile = join(sDataDir, 'sessionURI.log');
    log = None;
    logHandler = None;
    nRetryCount = RETRYCOUNT or 3;
    isShowProgress = SHOWPROGRESS or False;

    def __init__(self, isWeb=None, sDataDir=None):
        self.__dict__.update({
            key: value
            for (key, value) in type(self).__dict__.items()
            if not key.startswith('__') and not hasattr(value, '__call__')
        });
        if (isWeb is not None): self.isWeb = isWeb;
        if (sDataDir): self.sDataDir= sDataDir;
        if (not exists(self.sDataDir)): os.mkdir(self.sDataDir);
        if (self.isWeb):
            self.sRedirect = '{}://{}:{}/oauth'.format(SCHEME, HOST, PORT);
            self.sCodeLog = join(self.sDataDir, 'web_code.log');
            self.sTokenLog = join(self.sDataDir, 'web_token.log');
            self.sClientType = 'web';
        else:
            self.sRedirect = 'http://localhost:{}/oauth'.format(PORT);
            self.sCodeLog = join(self.sDataDir, 'local_code.log');
            self.sTokenLog = join(self.sDataDir, 'local_token.log');
            self.sClientType = 'installed';

        self.sClientFile = type(self).getClientPath(self);

        #logging.basicConfig(format= '    %(asctime)s %(levelname)-5s - %(filename)s:%(lineno)d - %(message)s');
        #logging.basicConfig(
        #        format= '    %(asctime)s %(levelname)-5s - %(filename)s:%(lineno)d:\n%(message)s',
        #        datefmt='%Y-%m-%d %H:%M:%S'
        #);
        formatter = logging.Formatter(
                fmt='    %(asctime)s %(levelname)-5s - %(filename)s:%(lineno)d:\t%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
        );
        self.logHandler = logHandler = logging.StreamHandler(sys.stdout);
        logHandler.setFormatter(formatter);
        self.log = log = logging.getLogger(__package__);
        log.handlers = [logHandler];
        log.setLevel(LOGLEVEL);
        log.propagate = False;
        #log.debug('configured.\napp type: {}\ndata directory: {}'.format(self.sClientType, self.sDataDir));

    def getClientPath(self):
        if (self.isWeb):
            sClient = WEBCLIENT;
        else:
            sClient = CLIENT;
        sClientFile = join(self.sDataDir, sClient);
        if (not exists(sClientFile)):
                sClientFile = join(self.sDir, sClient);
        if (not exists(sClientFile)):
            aFiles = [x for x in os.listdir(self.sDataDir) if x.startswith('client_secret')];
            if (aFiles):
                sClientFile = aFiles[0];
                sClientFile = os.path.join(self.sDataDir, sClientFile);
        if (not exists(sClientFile)):
            sClientFile = '';
        return sClientFile;

# the config object to be actually used
config = Config();
