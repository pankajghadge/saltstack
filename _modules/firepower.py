# -*- coding: utf-8 -*-
'''
Developer: pankaj ghadge
CISCO firepower Module
'''
# Import python libs
from __future__ import absolute_import, print_function, unicode_literals
#from urllib.parse import quote_plus
#from urlparse import quote_plus
from salt.ext import six
from salt.exceptions import CommandExecutionError
import salt.utils.json
import time
import logging
import sys


# Import third party libs
try:
    import requests
    #import utility as utl
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

log = logging.getLogger(__name__)

__virtualname__ = 'firepower'

def __virtual__():
    '''
    Load only if requests module is installed
    '''
    if HAS_LIBS:
        return __virtualname__
    return (False, 'CISCO firepower module cannot be loaded: python requests library not available.')

class FirepowerApi(object):
    def __init__(self, base_url, kwargs):

        #self.server = 'https://' + utl.e_var['FmcIp']
        self.server = base_url
        self.username = False
        self.password = False
        self.headers = []
        self.domain_uuid = ""
        self.authTokenTimestamp = 0

        for key in kwargs:
            if key == 'username':
                self.username = kwargs[key]
            elif key == 'password':
                self.password = kwargs[key]
        if self.username is False and self.password is False:
            raise CommandExecutionError('No authentication specified (user/password)')

    def get_auth_token(self):
        self.headers = {'Content-Type': 'application/json'}
        api_auth_path = "/api/fmc_platform/v1/auth/generatetoken"
        auth_url = self.server + api_auth_path
        domains = []
        try:
            r = requests.post(auth_url, headers=self.headers,
                              auth=requests.auth.HTTPBasicAuth(self.username, self.password), verify=False)
            auth_headers = r.headers
            auth_token = auth_headers.get('X-auth-access-token', default=None)
            self.domain_uuid = auth_headers.get('domain_uuid', default=None)
            self.headers['X-auth-access-token'] = auth_token
            self.authTokenTimestamp = int(time.time())

            #auth_token = r.headers['X-auth-access-token']
            domains = salt.utils.json.loads(r.headers['DOMAINS'])

            if auth_token is None:
                log.debug("auth_token not found. Exiting...")
                # raise Exception("Error occurred in get auth token ")
        except Exception as err:
            print(str(err))
            log.error("Error in generating auth token --> " + str(err))

        return auth_token,domains

    def request(self, url,action, data=''):
        '''To make a request to the API.'''

        # If we have data, convert to JSON
        if (isinstance(data, dict)):
            data = json.dumps(data)
            log.debug('Data to sent: %s' % data)

        self.get_auth_token()

        try:
            # REST call with SSL verification turned off:
            log.info("Request: " + url)

            if action == 'get':
               log.debug('GET request %s' % url)
               self.req = requests.get(url, headers=self.headers, verify=False)
            elif action == 'post':
               log.debug('POST request %s' % url)
               self.req = requests.post(url, headers=self.headers, verify=False, data=data)
            elif action == 'put':
               log.debug('PUT request %s' % url)
               self.req = requests.put(url, headers=self.headers, verify=False, data=data)
            elif action == 'delete':
               log.debug('DELETE request %s' % url)
               self.req = requests.delete(url, headers=self.headers, verify=False)

            if self.req.content == b'':
                result = None
                log.debug('No result returned.')
                #log.debug('Response status code is:' + self.req.status_code)
            else:
                result = self.req.json()
                #log.debug('Response status code is:' + self.req.status_code)
                if 'error' in result and result['error']:
                    raise CommandExecutionError(result['message'])

            status_code = self.req.status_code
            resp = r.text
            log.info("Response status_code: " + str(status_code))
            log.info("Response body: " + str(resp))
            if status_code == 200:
                pass
            else:
                r.raise_for_status()
                raise Exception("Error occurred in put -->" + resp)

        except requests.exceptions.RequestException as e:
            log.critical("Connection error for " + str(e))
            raise CommandExecutionError("Connection error for " + str(e))
        except ValueError as e:
            if self.req.status_code == 403:
                log.warning(url + " forbidden")
                raise CommandExecutionError(url + " forbidden")
            elif self.req.status_code == 404:
                log.warning(url + " forbidden")
                raise CommandExecutionError(url + " not found")
            else:
                message = ('%s: %s %s' % (e, self.req.url, self.req.text))
                log.debug(message)
                raise ValueError(message)
        finally:
            if self.req: self.req.close()
            return result

    def post(self, path, data=''):
        '''For post based requests.'''
        return self.request(path, 'post', data)

    def get(self, path):
        '''For get based requests.'''
        return self.request(path, 'get')

    def put(self, path, data=''):
        '''For put based requests.'''
        return self.request(path, 'put', data)

    def delete(self, path):
        '''For delete based requests.'''
        return self.request(path, 'delete')


def _exact_match(data_list, field, value):
    match = list(filter(lambda data: value == data[field] , data_list))
    return match

# Get network objects (all network and host objects)
def list_all_network(base_url, domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', **conn_args):
    firepowerconn = FirepowerApi(base_url, conn_args)
    api_path = "/api/fmc_config/v1/domain/{domain_id}/object/networkaddresses".format(domain_id=domain)
    url = firepowerconn.server + api_path + '?offset=0&limit=10000'
    result = firepowerconn.get(url)
    return result['items']

def get_network_objectid_by_name(base_url, name, domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', **conn_args):
    data = list_all_network(base_url, domain, **conn_args)
    for item in data:
        if item['type'] == 'Network' and item['name'] == name:
            return str(item['id'])
    return ''

#def get_network_objectid_by_name(base_url, name, domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', **conn_args):
#    firepowerconn = FirepowerApi(base_url, conn_args)
#    api_path = "/api/fmc_config/v1/domain/{domain_id}/object/networks".format(domain_id=domain)
#    url = firepowerconn.server + api_path + '?offset=0&limit=10000'
#
#    result = firepowerconn.get(url)
#    for item in result['items']:
#        if item['type'] == 'Network' and item['name'] == name:
#            return str(item['id'])
#    return ''

def list_all_host(base_url, domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', **conn_args):
    firepowerconn = FirepowerApi(base_url, conn_args)
    api_path = "/api/fmc_config/v1/domain/{domain_id}/object/hosts".format(domain_id=domain)
    url = firepowerconn.server + api_path + '?offset=0&limit=10000'
    result = firepowerconn.get(url)
    return result['items']

def get_host_objectid_by_name(base_url, name, domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', **conn_args):
    data = list_all_host(base_url, domain, **conn_args)
    for item in data:
        if item['type'] == 'Host' and item['name'] == name:
            return str(item['id'])
    return ''

def list_all_networkgroup(base_url, domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', **conn_args):
    firepowerconn = FirepowerApi(base_url, conn_args)
    api_path = "/api/fmc_config/v1/domain/{domain_id}/object/networkgroups".format(domain_id=domain)
    url = firepowerconn.server + api_path + '?offset=0&limit=10000'
    result = firepowerconn.get(url)
    return result['items']

def get_networkgroup_objectid_by_name(base_url, name, domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', **conn_args):
    data = list_all_networkgroup(base_url, domain, **conn_args)
    for item in data:
        if item['type'] == 'NetworkGroup' and item['name'] == name:
            return str(item['id'])
    return ''

def list_all_domains(base_url,**conn_args):
    firepowerconn = FirepowerApi(base_url, conn_args)
    (token, domains) = firepowerconn.get_auth_token()
    return domains

def get_domain_objectid_by_names(base_url, name, **conn_args):
    domains = list_all_domains(base_url, **conn_args)
    for domain in domains:
        if domain['name'] == name:
           return domain['uuid']
    return ''

#print(get_host_objectid_by_name("https://xx.xx.xx.xx", 'hostname1', username="test", password="test123"))
#print(get_network_objectid_by_name("https://xx.xx.xx.xx", 'hostname or groupname', username="test", password="test123"))
#print(get_networkgroup_objectid_by_name("https://xx.xx.xx.xx", 'hostname or groupname', domain='7e276abec-e0f2-11e3-8169-6d9ed49b625f', username="test", password="test123"))
#print(get_network_objectid_by_name("https://xx.xx.xx.xx", 'hostname or groupname', username="test", password="test123"))
#print(list_domains("https://xx.xx.xx.xx",username="test", password="test123"))
#print(get_domain_objectid_by_names("https://xx.xx.xx.xx", "Global", username="test", password="test123"))
#print(list_all_host("https://xx.xx.xx.xx", username="test", password="test123"))
#print(list_all_network("https://xx.xx.xx.xx", username="test", password="test123"))
#print(list_networkgroup("https://xx.xx.xx.xx", domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', username="test", password="test123"))
print(list_all_networkgroup("https://xx.xx.xx.xx", domain='e276abec-e0f2-11e3-8169-6d9ed49b625f', username="test", password="test123"))
