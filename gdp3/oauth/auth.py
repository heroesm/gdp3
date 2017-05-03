#! /usr/bin/env python3

import urllib.request
import urllib.parse
import json
#from pprint import pprint
import time
import webbrowser
import logging

from ..config import config

global sRedirect
global log

log = logging.getLogger(__name__);
sRedirect = config.sRedirect;

def auth(sClientFile=None, *, sId=None, sAuthUrl=None):
    def extractArg():
        # get arguments needed to fetch application code
        global log
        nonlocal sClientFile, sId, sAuthUrl
        if (sId):
            log.debug('load client ID from arguments');
            if (not sAuthUrl):
                sAuthUrl = 'https://accounts.google.com/o/oauth2/auth';
        else:
            if (not sClientFile):
                sClientFile = config.sClientFile;
            log.debug('load client info from file "{}"'.format(sClientFile));
            with open(sClientFile, 'r') as file:
                sData = file.read();
            m1 = json.loads(sData);
            m1 = m1[config.sClientType]
            sAuthUrl = m1['auth_uri'];
            sId = m1['client_id'];
        mArgs = {
            'client_id': sId,
            'redirect_uri': sRedirect,
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.appfolder',
            'state': str(time.ctime()),
        };
        if (config.sClientType == 'web'):
            mArgs.update({
                'access_type': 'offline',
                'include_granted_scopes': 'true',
            });
        return sAuthUrl, mArgs;

    def doConsent(sUrl):
        global log
        if (config.sClientType != 'web'):
            webbrowser.open(sUrl);
        print('open URL below in local browser:');
        print('\n', sUrl, '\n');
        return True;

    sAuthUrl, mArgs = extractArg();
    sUrl = '{}?{}'.format(sAuthUrl, urllib.parse.urlencode(mArgs, True));
    doConsent(sUrl);

def main():
    auth();

if __name__ == '__main__':
    main();
