# -*- coding: utf-8 -*-
'''
Written by: ghadge.pankaj@gmail.com
Calling cedexis API for purging data on CDN
'''

# Import python libs
from __future__ import absolute_import, print_function, unicode_literals
import logging
import os
import re
from urlparse import urlsplit
import urllib

# Import salt libs
import salt.utils.files
import salt.utils.json
import salt.utils.http

log = logging.getLogger(__name__)
url_oauth = 'https://api.cedexis.com/api/oauth/token'
url_api   = 'https://api.cedexis.com/api/v2/actions/fusion/purge.json'

def _get_oauth2_access_token(client_key, client_secret):

    global url_oauth
    '''
    Query the cedexis API and get an access_token
    '''
    if not client_key and not client_secret:
        log.error(
            "client_key and client_secret has not been specified"
            "and are required parameters."
        )
        return False

    method = 'POST'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    params = {
        'grant_type': 'client_credentials',
        'client_id': client_key,
        'client_secret': client_secret
    }

    resp = salt.utils.http.query(
        url=url_oauth,
        method=method,
        header_dict=headers,
        params=params
    )

    respbody = resp.get('body', None)
    log.debug(respbody)
    if not respbody:
        log.error("Could not get the response from cedexis oauth api. Please check connection.")
        return False

    access_token = salt.utils.json.loads(respbody)['access_token']
    return access_token



def purge(platformIds, client_key, client_secret, uris=None, uris_file=None):
    global url_api
    url_list = []
    ret = {
        'result': False,
        'comment': 'uris not found'
    }
    url_found = False

    if uris is not None and uris_file is not None:
        ret['comment'] = "You can't provide both uris and uris_file, pass uris or uris_file"
        return ret

    if uris_file is not None:
        if any(uris_file.startswith(proto) for proto in ('salt://', 'http://', 'https://', 'swift://', 's3://')):
            uris_file = __salt__['cp.cache_file'](uris_file)

        if os.path.exists(uris_file):
            with salt.utils.files.fopen(uris_file, 'r') as ifile:
                uris = salt.utils.stringutils.to_unicode(ifile.read())
        else:
            log.error('File "%s" does not exist', uris_file)
            ret['comment'] = 'File {} does not exist'.format(uris_file)
            return ret
    elif uris is None:
         ret['comment'] = "please provide value for uris"
         return ret

    for line in uris.splitlines():
        line = line.strip()
        if re.match(r'#', line):  # ignore sql comments
            continue
        url_found = True
        line = urllib.quote(line)
        line_ob = urlsplit(line)
        line = line_ob.path

        if not line.startswith('/'):
           line = '/' + line

        url_list.append(line)

    if not url_found:
        return ret


    access_token = _get_oauth2_access_token(client_key, client_secret)
    if not access_token:
        ret['comment'] = "Unable to generate token, please check client_key and client_secret"
        return ret

    authstring = 'Bearer {0}'.format(access_token)

    headers = {
        'Authorization': authstring,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    data = {
        'uris': url_list,
        'platformIds': platformIds.split(':')
    }

    method = 'POST'
    resp = salt.utils.http.query(
        url=url_api,
        method=method,
        header_dict=headers,
        data=salt.utils.json.dumps(data)
    )

    respbody = resp.get('body', None)
    log.debug(respbody)

    if not respbody:
        ret['comment'] = "Request denied by cedexis API"
        return ret

    respbodydict = salt.utils.json.loads(resp['body'])
    ret['comment'] = respbodydict
    ret['result'] = True

    return ret
