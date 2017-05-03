import os
import sys
import urllib
import logging

log = logging.getLogger(__name__);

def prepareDir():
    global sHome
    global sDir
    # cd to the directory of running script
    sPath = sys.argv[0] if __name__ == '__main__' else __file__;
    sDir = os.path.split(sPath)[0];
    if (sDir): os.chdir(sDir);
    sHome = os.path.expanduser('~');

def mergeQuery(sUrl, mQuery):
    parts = urllib.parse.urlsplit(sUrl);
    scheme, netloc, path, query, fragment = parts;
    mQueryNew = urllib.parse.parse_qs(query);
    mQueryNew.update(mQuery);
    query = urllib.parse.urlencode(mQueryNew, doseq=True);
    parts = scheme, netloc, path, query, fragment;
    sUrl = urllib.parse.urlunsplit(parts);
    return sUrl

def loadFromFile(sFile=None, nCursor=None):
    # split file data to avoid large memory consumption and to display upload process
    global log
    if (not sFile): sFile;
    if (not nCursor): nCursor;
    with open(sFile, 'rb') as file:
        file.seek(nCursor);
        log.debug('reading from bytes {} in file {}'.format(file.tell(), sFile));
        sys.stdout.write('\n');
        n = 1024**2;
        i = 1;
        bData = file.read(n);
        while (bData):
            yield bData
            sys.stdout.write('\r{} MB processed'.format(i));
            bData = file.read(n);
            i += 1;
    sys.stdout.write('\n');

def writeToFile(res, sFile):
    with open(sFile, 'xb') as file:
        log.info('start downloading to file "{}"'.format(sFile));
        n = 1024**2;
        i = 1;
        bData = res.read(n);
        sys.stdout.write('\n');
        while bData:
            file.write(bData);
            sys.stdout.write('\r{} MB downloaded'.format(i));
            bData = res.read(n);
            i += 1;
        sys.stdout.write('\n');
        log.info('download completed');
        return sFile
