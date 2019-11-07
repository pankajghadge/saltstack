# -*- coding: utf-8 -*-
'''
SaltStack formula and code for cedexis
Written by: Pankaj.GHADGE@3ds.com
Calling cedexis API for purging data on CDN
Installation:
  1. Copy state cedexis.py file under _state folder
  2. Copy module cedexis.py file under _module folder
  3. Run command: salt "*" saltutil.sync_all
    
==========================
The cedexis module is used to call API of cedexis and purge the URLs.
Ref:
   https://github.com/cedexis/webservices/wiki/v2-Action-Endpoints
   https://github.com/cedexis/webservices/wiki/v2-Access-Control (Auth and access token using Oauth)

   platformIds are separated by colon

   purge_companion_cdn:
     cedexisi.purge:
       - uris: |
           /css/example1.css
           /css/example2.css
       - platformIds: "11c64b:55c63e"
       - client_id: "fusion_client_id"
       - client_secret: "client_secret" 

   purge_file_companion_cdn:
     cedexis.purge:
       - uris_file: /data/cdn_purge_files/example1.txt
       - platformIds: "11c64b:55c63e"
       - client_id: "fusion_client_id"
       - client_secret: "client_secret"

   curl https://api.cedexis.com/api/oauth/token \
   -d 'client_id=YOUR_CLIENT_ID' \
   -d 'client_secret=YOUR_CLIENT_SECRET' \
   -d 'grant_type=client_credentials'

   Use above access_token to make API requests:

   curl https://api.cedexis.com/api/v2/meta/system.json/ping \
   -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'

   You should see a response containing the current server time:
   {
       "result":"pong"
   }

'''
# Import python libs
from __future__ import absolute_import, print_function, unicode_literals

# Import Salt libs


def __virtual__():
    '''
    Only load if the cedexis module is available in __salt__
    '''
    return 'cedexis.purge' in __salt__

def purge(name,
        platformIds,
        client_id,
        client_secret,
        uris=None,
        uris_file=None):
    '''
    name
         Used only as an ID
    uris
         List of URLs to be purged
    platformIds
         List of IDs mentioned in CDN Purge Adapters for particular Host
    client_id
         client id, which you need to call the sign-in Cedexis API
         Locatoin: Cedexis Portal -> My Account -> API -> OAuth Configuration
    client_secret
         client_secret is essentially a password - it is precious, keep it secret, keep it safe
         Location: Cedexis Portal -> My Account -> API -> OAuth Configuration

    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Cedexis API call'}

    '''
    if uris is not None and not isinstance(uris, list):
        ret['comment'] = ('Invalidly-formatted \'uris\' parameter')
        return ret
    '''

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'The action will purge the uris on respective CDN'
        return ret

    response = __salt__['cedexis.purge'](platformIds, client_id, client_secret, uris=uris, uris_file=uris_file)

    if response['result'] is False:
        ret['result'] = False
        ret['comment'] = response['comment']
        return ret

    ret['changes']['api_call'] = "Cedexis API call Sucessfully"
    ret['comment'] = response['comment']

    return ret
