#! /usr/bin/env python3

import os
from os.path import split, join, exists, abspath
#import urllib.request
#import sys
import logging
import re
import urllib.error
import argparse

from gdp3.localfile import File
from gdp3.cloudfile import CloudFile
from gdp3.tokenfile import Token

TOKENFILE = 'token1.json'
FILE = '';
DIR = '';
DIRPATTERN = r'';
SUPERDIR = '';
DEBUGLEVEL = logging.DEBUG;
UNIQUE = True;

sHome = '';
sDir = '';
log = None;

def prepare():
    global DEBUGLEVEL
    global sHome
    global sDir
    global log
    sHome = os.path.expanduser('~')
    sDir = os.path.split(__file__);
    logging.basicConfig();
    log = logging.getLogger(__name__);
    log.setLevel(DEBUGLEVEL);
prepare();

def parseArg():
    global TOKENFILE, FILE, DIR, DIRPATTERN, SUPERDIR, DEBUGLEVEL, UNIQUE
    global log
    parser = argparse.ArgumentParser(description='upload certain file to certain directory under cetain super directory in google drive');
    parser.add_argument('-t', '--token',
            help='name of the json file containing access token or refresh token'
    );
    parser.add_argument('-v', '--verbose',
            action='store_true',
            help='show verbose debug information'
    );
    parser.add_argument('file',
            help='path of file to be uploaded'
    );
    group1 = parser.add_mutually_exclusive_group();
    group1.add_argument('-d', '--dir',
            help='name of remote directory, in google drive, to be uploaded into'
    );
    group1.add_argument('-p', '--pattern',
            help='pattern applied to the file uploading to extract the directory name, using the first group ( DIRNAME = MATCH.group(1) ); take care of back slash iterpretation!'
    );
    parser.add_argument('-s', '--super',
            help='name of the fixed super directory containing all the created sub directories holding uploaded files'
    );
    parser.add_argument('-u', '--unique',
            action=('store_true'),
            help='upload only when there is no file with the same name under the same directory'
    );
    args = parser.parse_args();
    TOKENFILE = args.token or TOKENFILE or '';
    if (args.verbose):
        DEBUGLEVEL = logging.DEBUG;
    else:
        DEBUGLEVEL = logging.INFO;
    log.setLevel(DEBUGLEVEL);
    FILE = args.file or FILE or '';
    DIR = args.dir or DIR or '';
    DIRPATTERN = args.pattern or DIRPATTERN or r'';
    SUPERDIR = args.super or SUPERDIR or '';
    UNIQUE = bool(args.unique);
    log.debug('passed command line arguments: {}'.format(
        {key: value for (key, value) in vars(args).items() if value is not None}
    ));
    return True;


def getDir(sDir, token, sSuperDir=None):
    global SUPERDIR;
    sSuperDir = sSuperDir or SUPERDIR or '';
    sSuperDir = sSuperDir.strip();
    root = CloudFile('root', token)
    if (sSuperDir and sSuperDir != 'root'):
        aFiles = root.getDirChildren(sSuperDir);
        if (aFiles):
            superDir = aFiles[0];
        else:
            superDir = root.mkdir(sSuperDir);
    else:
        superDir = root;
    if (not sDir):
        return superDir;
    else:
        aFiles = superDir.getDirChildren(sDir);
        if (aFiles):
            dir1 = aFiles[0];
        else:
            dir1 = superDir.mkdir(sDir);
        return dir1;

def uploadToDir(sFile, sDir=None, directory=None, sName=None, token=None, sToken=None, sSuperDir=None, mMeta=None, isUnique=True):
    # directory precede sDir
    assert sDir or directory;
    if (not token):
        if (not sToken):
            assert TOKENFILE;
            sToken = TOKENFILE;
        token = Token(sToken);
    assert token;
    sName = sName or os.path.split(sFile)[1];
    if (directory):
        targetDir = directory;
        sNetPath = '{}/{}'.format(directory.sName, sName);
    else:
        targetDir = getDir(sDir, token, sSuperDir);
        sNetPath = '/{}/{}/{}'.format(sSuperDir, sDir, sName);
    mMeta = mMeta or {};
    if (isUnique is None):
        isUnique = True;
    if (isUnique):
        aFiles = targetDir.getChildren(sName);
        if (aFiles):
            log.info('{} existed, uploading aborted'.format(sNetPath));
            return False;
    sDirId = targetDir.sId;
    aParents = [sDirId];
    mMeta.update({
            'parents': aParents
    });
    file = File(sFile, token, mMeta=mMeta, sName=sName);
    log.debug('uploading {} into {}'.format(file, targetDir));
    isDone = False;
    while not isDone:
        try:
            if (file.loadSession() or file.initSession()):
                isDone = file.upload();
            else:
                isDone = True;
        except urllib.error.URLError as e:
            log.error('error occured while uploading: "{}", retrying...'.format(e));
            isDone = False;
    return file.sId;

def upload(sFile):
    global TOKENFILE
    global DIR
    global DIRPATTERN
    global SUPERDIR
    global UNIQUE
    global log
    assert TOKENFILE;
    token = Token(TOKENFILE);
    isUnique = bool(UNIQUE);
    sDir = (DIR or '').strip();
    if (not sDir and DIRPATTERN):
        pattern = re.compile(DIRPATTERN);
        match = pattern.search(sFile);
        if (match):
            sDir = match.group(1);
    log.info('uploading file "{}" to directory "{}" under super directory "{}"'.format(sFile, sDir, SUPERDIR));
    sFileId = uploadToDir(sFile, sDir, token=token, isUnique=isUnique);
    if (sFileId):
        file = CloudFile(sFileId, token);
        file.getMetadata();
        return file;

def main():
    global FILE
    parseArg();
    sFile = FILE;
    upload(sFile);

if __name__ == '__main__':
    main();
