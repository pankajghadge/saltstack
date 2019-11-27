# -*- coding: utf-8 -*-
'''
Written by: ghadge.pankaj@gmail.com
Calling cedexis API for purging data on CDN
'''

# Import python libs
from __future__ import absolute_import, print_function, unicode_literals
import logging
import urllib
import os
import requests, sys
import re

# Import salt libs
import salt.utils.files
import salt.utils.json
from salt.utils.decorators import depends

if sys.version_info[0] >= 3:
   # python3
   from urllib import parse
else:
   # python2.7
   import urlparse as parse

log = logging.getLogger(__name__)

try:
   from akamai.edgegrid import EdgeGridAuth
   HAS_EDGEGRID_PYTHON = True
except ImportError:
   HAS_EDGEGRID_PYTHON = False

__virtualname__ = 'akamai'

def __virtual__():
    '''
    Load module only if edgegrid-python installed
    pip install edgegrid-python
    '''
    if HAS_EDGEGRID_PYTHON:
        return __virtualname__
    return (False, 'The akamai execution module not loaded: python edgegrid-python library not found.')

def _akamai_edgegrid_req():
    '''
    Fallback function stub
    '''
    return 'Need "edgegrid-python" installed for this function'

def purge(client_secret, host, access_token, client_token, uris=None, uris_file=None, headers=None):
    '''
    uris
         List of URLs to be purged
    uris_file
         List of URLs in file to be purged
    client_secret
         client_secret is essentially a password - it is precious, keep it secret, keep it safe
    access_token
         Akamai Authorization Server uses to exchange an authorization grant for an access token
    client_token
         client tokens to access any Akamai API
    host
         Akamai api host generated using Identity and access Management
    '''

    url_list = []
    baseurl  = '%s://%s/' % ('https', host)
    endpoint = '/ccu/v3/invalidate/url'
    ret = {
        'result': False,
        'comment': 'uris not found'
    }
    url_found = False
    parameters=None
    action = "invalidate"

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
         ret['comment'] = 'please provide value for uris'
         return ret

    for line in uris.splitlines():
        line = line.strip()
        if re.match(r'#', line):  # ignore comments
            continue
        if not line:
            continue
        url_found = True
        url_list.append(line)

    if not url_found:
        return ret

    session = requests.Session()
    # Set the config options
    session.auth = EdgeGridAuth(
            client_token=client_token,
            client_secret=client_secret,
            access_token=access_token
    )

    if headers:
       session.headers.update(headers)

    purge_obj = { "objects" : url_list }
    headers = {'content-type': 'application/json'}
    body = salt.utils.json.dumps(purge_obj)

    log.debug("Adding %s request to queue - %s" % (action, body));
    endpoint_result = session.post(parse.urljoin(baseurl, endpoint),
                                   data=body,
                                   headers=headers,
                                   params=parameters
    )
    status = endpoint_result.status_code
    log.debug("LOG: POST %s %s %s" % (endpoint, status, endpoint_result.headers["content-type"]))

    '''
    if status == 204:
       ret['comment'] = "Record updated successfully!"
       ret['result'] = True
       return ret
    '''
    endpoint_result_json = salt.utils.json.dumps(endpoint_result.json())
    log.debug(">>>\n" + endpoint_result_json + "\n<<<\n")

    if (status in (403, 400, 401, 404)):
        ret['comment'] = _get_http_errors(status, endpoint, endpoint_result.json())
        return ret

    ret['comment'] = endpoint_result_json
    ret['result'] = True

    return ret

def _get_http_errors(status_code, endpoint, result):

    error_msg = ""
    if not isinstance(result, list):
       details = result.get('detail') or result.get('details') or ""
    else:
       details = ""

    if status_code == 403:
       error_msg =  "ERROR: Call to %s failed with a 403 result\n" % endpoint
       error_msg += "ERROR: This indicates a problem with authorization.\n"
       error_msg += "ERROR: Please ensure that the credentials you created for this script\n"
       error_msg += "ERROR: have the necessary permissions in the Luna portal.\n"
       error_msg += "ERROR: Problem details: %s\n" % details
       return error_msg

    if status_code in [400, 401]:
       error_msg =  "ERROR: Call to %s failed with a %s result\n" % (endpoint, status_code)
       error_msg += "ERROR: This indicates a problem with authentication or headers.\n"
       error_msg += "ERROR: Problem details: %s\n" % result
       return error_msg

    if status_code in [404]:
       error_msg =  "ERROR: Call to %s failed with a %s result\n" % (endpoint, status_code)
       error_msg += "ERROR: This means that the page does not exist as requested.\n"
       error_msg += "ERROR: Please ensure that the URL you're calling is correctly formatted\n"
       error_msg += "ERROR: or look at other examples to make sure yours matches.\n"
       error_msg += "ERROR: Problem details: %s\n" % details
       return error_msg

    error_string = None

    if "errorString" in result:
       if result["errorString"]:
          error_string = result["errorString"]
    else:
       for key in result:
          if type(key) is not str or isinstance(result, dict) or not isinstance(result[key], dict):
            continue
          if "errorString" in result[key] and type(result[key]["errorString"]) is str:
            error_string = result[key]["errorString"]

    if error_string:
       error_msg =  "ERROR: Call caused a server fault.\n"
       error_msg += "ERROR: Please check the problem details for more information:\n"
       error_msg += "ERROR: Problem details: %s\n" % error_string
       return error_msg

    return error_msg
