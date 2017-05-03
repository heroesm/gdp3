# google drive in python3
Native python3 google drive client library implementing oauth2 authentication and REST API v3.

## gdp3
The library realising DRIVE REST API v3 and providing a one-off oauth2 authentication programme.
Some constants at the top of config.py should be modified before using this library
* oauth: scripts fulfiling oauth2 steps;
* doauth.py: using scripts from oauth to make one oauth2 authentication;
* tokenfile.py: a class abstracting authorisation token of the API and the local file storing token-related information;
* localfile.py: a class abstracting local file to be uploaded and the resumable upload procedure;
* cloudfile.py: a class abstracting file stored on google drive and interactions associated with the file;
* config.py: containing all the configurable and some environmental constants of the whole library; 
* utility.py: meaningless and not used.

## upload.py
A reference script makes use of the gdp3 library; modify some variables at the top of the file before use it.
```
$ python3 upload.py -h
usage: upload.py [-h] [-t TOKEN] [-v] [-d DIR | -p PATTERN] [-s SUPER] [-u]
                 file

upload certain file to certain directory under cetain super directory in
google drive

positional arguments:
  file                  path of file to be uploaded

optional arguments:
  -h, --help            show this help message and exit
  -t TOKEN, --token TOKEN
                        name of the json file containing access token or
                        refresh token
  -v, --verbose         show verbose debug information
  -d DIR, --dir DIR     name of remote directory, in google drive, to be
                        uploaded into
  -p PATTERN, --pattern PATTERN
                        pattern applied to the file uploading to extract the
                        directory name, using the first group ( DIRNAME =
                        MATCH.group(1) ); take care of back slash
                        iterpretation!
  -s SUPER, --super SUPER
                        name of the fixed super directory containing all the
                        created sub directories holding uploaded files
  -u, --unique          upload only when there is no file with the same name
                        under the same directory
```
