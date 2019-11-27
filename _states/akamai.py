# -*- coding: utf-8 -*-
'''
Written by: ghadge.pankaj@3ds.com
Calling Akamai API for purging data on CDN
==========================

   purge_project_name_cdn:
     akamai.purge:
       - uris: |
           https://domain_name.com/css/style.css
           https://domain_name.com/js/example.js
       - client_secret: 'enter_client_secret'
       - host: 'host_provided_by_akamai'
       - access_token: 'enter_access_token'
       - client_token: 'enter_client_token'

   purge_file_project_name_cdn:
     akamai.purge_file:
       - uris_file: /data/tmp/akamai_purge_file.txt
       - client_secret: 'enter_client_secret'
       - host: 'host_provided_by_akamai'
       - access_token: 'enter_access_token'
       - client_token: 'enter_client_token'

   Get Started with Akamai APIs:
   https://developer.akamai.com/api/getting-started
   Note: Make sure edgegrid-python package is installed using 'pip install edgegrid-python'
'''
# Import python libs
from __future__ import absolute_import, print_function, unicode_literals
# Import Salt libs

def __virtual__():
    '''
    Only load if the cedexis module is available in __salt__
    '''
    return 'akamai.purge' in __salt__

def purge(name,
        client_secret,
        access_token,
        client_token,
        host,
        uris=None,
        uris_file=None):
    '''
    name
         Used only as an ID
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

    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Akamai API call'}

    if uris is not None and uris_file is not None:
       ret['comment'] = "You can't provide both uris and uris_file, pass uris or uris_file"
       ret['result'] = False
       return ret

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'The action will purge the uris on respective CDN'
       return ret

    response = __salt__['akamai.purge'](client_secret=client_secret,
                                        host=host,
                                        access_token=access_token,
                                        client_token=client_token,
                                        uris=uris,
                                        uris_file=uris_file
    )

    if response['result'] is False:
       ret['result'] = False
       ret['comment'] = response['comment']
       return ret

    #ret['changes']['api_call'] = "akamai API call Sucessfully"
    ret['comment'] = response['comment']
    return ret
