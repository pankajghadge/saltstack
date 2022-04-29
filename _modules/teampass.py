# -*- coding: utf-8 -*-
'''
Written by: pankaj ghadge
Team Password manager Module
'''
# Import python libs
from __future__ import absolute_import, print_function, unicode_literals
#from urllib.parse import quote_plus
#from urlparse import quote_plus
from salt.ext import six
from salt.exceptions import CommandExecutionError
import salt.utils.json
import hmac
import hashlib
import time
#import urllib
import sys
import re
import json
import logging

if sys.version_info >= (3, 0):
   from urllib.parse import quote_plus
if sys.version_info < (3, 0) and sys.version_info >= (2, 5):
   from urllib import quote_plus

# Import third party libs
try:
    import requests
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False


log = logging.getLogger(__name__)

__virtualname__ = 'teampass'

def __virtual__():
    '''
    Load only if requests module is installed
    '''
    if HAS_LIBS:
        return __virtualname__
    return (False, 'Team Password Manager module cannot be loaded: python requests library not available.')

class TpmApi(object):
    '''
       Settings needed for the connection to Team Password Manager.

       Args:
       base_url    : Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key
                     (Online Doc) https://teampasswordmanager.com/docs/api-authentication/
    '''

    def __init__(self, base_url, kwargs):

        self.apiurl = 'api/' + 'v4' + '/'
        log.debug('Set as apiurl: %s' % self.apiurl)
        self.api = self.apiurl
        self.base_url = base_url + '/index.php/'
        log.debug('Set Base URL to %s' % self.base_url)
        self.url = self.base_url + self.apiurl
        log.debug('Set URL to %s' % self.url)

        # set headers
        self.headers = {'Content-Type': 'application/json; charset=utf-8'}
        log.debug('Set header to %s' % self.headers)

        # check kwargs for either keys or user credentials
        self.private_key   = False
        self.public_key    = False
        self.username      = False
        self.password      = False
        self.unlock_reason = False

        for key in kwargs:
            if key == 'private_key':
                self.private_key = kwargs[key]
            elif key == 'public_key':
                self.public_key = kwargs[key]
            elif key == 'username':
                self.username = kwargs[key]
            elif key == 'password':
                self.password = kwargs[key]
            elif key == 'unlock_reason':
                self.unlock_reason = kwargs[key]
        if self.private_key is not False and self.public_key is not False and\
                self.username is False and self.password is False:
            log.debug('Using Private/Public Key authentication.')
        elif self.username is not False and self.password is not False and\
                self.private_key is False and self.public_key is False:
            log.debug('Using Basic authentication.')
        else:
            raise CommandExecutionError('No authentication specified (user/password or private/public key)')

    def request(self, path, action, data=''):
        '''To make a request to the API.'''
        # Check if the path includes URL or not.
        head = self.base_url
        if path.startswith(head):
            path = path[len(head):]
            #path = quote_plus(path, safe='/')
            path = quote_plus(path, safe='/')
        if not path.startswith(self.api):
            path = self.api + path
        log.debug('Using path %s' % path)

        # If we have data, convert to JSON
        if data:
            data = json.dumps(data)
            log.debug('Data to sent: %s' % data)
        # In case of key authentication
        if self.private_key and self.public_key:
            timestamp = str(int(time.time()))
            log.debug('Using timestamp: {}'.format(timestamp))
            unhashed = path + timestamp + str(data)
            log.debug('Using message: {}'.format(unhashed))
            self.hash = hmac.new(str.encode(self.private_key), msg=unhashed.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
            log.debug('Authenticating with hash: %s' % self.hash)
            self.headers['X-Public-Key'] = self.public_key
            self.headers['X-Request-Hash'] = self.hash
            self.headers['X-Request-Timestamp'] = timestamp
            auth = False
        # In case of user credentials authentication
        elif self.username and self.password:
            auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        # Set unlock reason
        if self.unlock_reason:
            self.headers['X-Unlock-Reason'] = self.unlock_reason
            log.info('Unlock Reason: %s' % self.unlock_reason)
        url = head + path
        # Try API request and handle Exceptions
        try:
            if action == 'get':
                log.debug('GET request %s' % url)
                self.req = requests.get(url, headers=self.headers, auth=auth, verify=False)
            elif action == 'post':
                log.debug('POST request %s' % url)
                self.req = requests.post(url, headers=self.headers, auth=auth,verify=False, data=data)
            elif action == 'put':
                log.debug('PUT request %s' % url)
                self.req = requests.put(url, headers=self.headers, auth=auth, verify=False, data=data)
            elif action == 'delete':
                log.debug('DELETE request %s' % url)
                self.req = requests.delete(url, headers=self.headers, verify=False, auth=auth)

            if self.req.content == b'':
                result = None
                log.debug('No result returned.')
                #log.debug('Response status code is:' + self.req.status_code)
            else:
                result = self.req.json()
                #log.debug('Response status code is:' + self.req.status_code)
                if 'error' in result and result['error']:
                    raise CommandExecutionError(result['message'])

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

    def get_collection(self, path):
        '''To get pagewise data.'''
        while True:
            items = self.get(path)
            req = self.req
            for item in items:
                yield item
            if req.links and req.links['next'] and\
                    req.links['next']['rel'] == 'next':
                path = req.links['next']['url']
            else:
                break

    def collection(self, path):
        '''To return all items generated by get collection.'''
        data = []
        for item in self.get_collection(path):
            data.append(item)
        return data

def _exact_match(data_list, field, value):
    match = filter(lambda data: value == data[field] , data_list)
    return match

def list_projects(base_url, **conn_args):
    '''
       List projects:
       Api Doc URL : https://teampasswordmanager.com/docs/api-projects/#list_projects
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       return the projects that the user has access to.
       The returned data is the same as in the projects lists (all active, archived, favorite and search) in the web interface.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List all projects.')
    return tpmconn.collection('projects.json')

def list_projects_archived(base_url, **conn_args):
    '''
       List archived projects:
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#list_projects
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       return the archived projects that the user has access to.
       The returned data is the same as in the projects list archived in the web interface.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List all archived projects.')
    return tpmconn.collection('projects/archived.json')

def list_projects_favorite(base_url, **conn_args):
    '''
       List favorite projects.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#list_projects
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       return the favorite projects that the user has access to.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List all favorite projects.')
    return tpmconn.collection('projects/favorite.json')

def list_projects_search(base_url, searchstring, exact_match = False, **conn_args):
    '''
       List projects with searchstring.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#list_projects
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       return the search string projects that the user has access to.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List all projects with: %s' % searchstring)
    projects = tpmconn.collection('projects/search/%s.json' % quote_plus(searchstring))

    if exact_match == False:
       return projects
    return _exact_match(projects, 'name', searchstring)


def show_project(base_url, id, **conn_args):
    '''
       Show a project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#show_project
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       returns all the data of a project, identified by its internal id.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('Show project info: %s' % id)
    return tpmconn.get('projects/%s.json' % id)

def list_passwords_of_project(base_url, id, **conn_args):
    '''
       List passwords of project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#list_pwds_prj
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       returns the passwords of a project, identified by its internal id.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List passwords of project: %s' % id)
    return tpmconn.collection('projects/%s/passwords.json' % id)

def list_user_access_on_project(base_url, id, **conn_args):
    '''
       List users who can access a project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#list_users_prj
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      returns the effective permissions users have on a project
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List User access on project: %s' % id)
    return tpmconn.collection('projects/%s/security.json' % id)

def create_project(name, base_url, data, **conn_args):
    '''
       Create a project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#create_project
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       data        :  Data for the project (name and parent_id are required)
                      {
                        "name": "Name of the project",
                        "parent_id": 20,
                        "tags": "tag1,tag2,tag3",
                        "notes": "some notes"
                      }
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 201 Created with the internal id of the project in the response body
    '''

    data['name'] = name
    if 'parent_id' not in data:
        data['parent_id'] = 0

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Create project: %s' % data)
    new_id = tpmconn.post('projects.json', data).get('id')
    log.info('Project has been created with id %s' % new_id)
    return new_id

def update_project(name, base_url, id, data, **conn_args):
    '''
       Update a project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#update_project
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project
       Data        : The request body must include the data for the project.
                     Only the fields that are included are updated, the other fields are left unchanged
                     {
                       "name": "Name of the project",
                       "tags": "tag1,tag2,tag3",
                       "notes": "some notes"
                     }
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    data['name'] = name
    tpmconn = TpmApi(base_url, conn_args)
    log.info('Update project %s with %s' % (id, data))
    tpmconn.put('projects/%s.json' % id, data)

    return True

def change_parent_of_project(base_url, id, new_parrent_id, **conn_args):
    '''
      Change parent of project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#change_parent
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url       : Your Team Password Manager URL
       id             : Internal id of the project
       new_parrent_id : It is the id of the new parent of the project
       **conn_args    : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                        (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.

    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Change parrent for project %s to %s' % (id, new_parrent_id))
    data = {'parent_id': new_parrent_id}
    tpmconn.put('projects/%s/change_parent.json' % id, data)

    return True

def update_security_of_project(base_url, id, data, **conn_args):
    '''
       Update security of project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#update_project_security
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project
       data        : Data for the project's security includes
                     managed_by          : id of the user that is to be the main manager. Can be any user except read only users.
                     grant_all_permission: id of the permission to grant all users. Allowed values:
                     -1 - (Do not set): set permissions for individual users/groups, not globally.
                     0 - No access: the user/group cannot access the project or any of its passwords.
                     10 - Traverse: the user/group can see the project name only.
                     20 - Read: the user/group can only read project data and its passwords.
                     30 - Read / Create passwords: the user/group can read project data and create passwords in it.
                     40 - Read / Edit passwords data: the user/group can read project data and edit the data of its passwords (and also create passwords).
                     50 - Read / Manage passwords: the user/group can read project data and manage its passwords (and also create passwords).
                     60 - Manage: the user/group has total control over the project and its passwords.
                     99 - Inherit from parent: the user/group will inherit the permission set on the parent project.
                          Cannot be set if the project is a root project.

                     users_permissions: Array of [user_id, permission_id]. User permissions will be set for the users passed.
                                        Deleting the current permissions.
                                        permission_id can be: 0, 10, 20, 30, 40, 50, 60, 99 (only 0, 10, 20, 99 for users with role read only).
                                        If you want to set (-1: Do not set), simply exclude the user.
                                        Admin users and the project manager can be included in this list, but it will have no effect.
                     groups_permissions: Array of [group_id, permission_id]. Groups permissions will be set for the groups passed
                                         Deleting the current permissions.
                                         permission_id can be:0, 10, 20, 30, 40, 50, 60, 99.
                                         If you want to set (-1: Do not set), simply exclude the group from the list.
                     {
                       "managed_by": 4,
                       "grant_all_permission": -1,
                       "users_permissions": [ [2,60], [3,10] ],
                       "groups_permissions": [ [1,40] ]
                     }

       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Update project %s security %s' % (id, data))
    tpmconn.put('projects/%s/security.json' % id, data)

    return True

def archive_project(base_url, id, **conn_args):
    '''
       Archive a project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#arch_unarch_project
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Archive project %s' % id)
    tpmconn.put('projects/%s/archive.json' % id)

    return True

def unarchive_project(base_url, id, **conn_args):
    '''
       Un-Archive a project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#arch_unarch_project
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Unarchive project %s' % id)
    tpmconn.put('projects/%s/unarchive.json' % id)

    return True

def delete_project(base_url, id, **conn_args):
    '''
       Delete a project.
       API Doc URL : https://teampasswordmanager.com/docs/api-projects/#delete_project
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Delete project %s' % id)
    tpmconn.delete('projects/%s.json' % id)

    return True

def list_passwords(base_url, **conn_args):
    '''
       List passwords.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#list_passwords
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

        return the passwords that the user has access to.
        The returned data is the same as in the passwords lists (all active, archived, favorite and search)
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List all passwords.')
    return tpmconn.collection('passwords.json')

def list_passwords_archived(base_url, **conn_args):
    '''
       List archived passwords.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#list_passwords
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key
       return the archived passwords that the user has access to.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List archived passwords.')
    return tpmconn.collection('passwords/archived.json')

def list_passwords_favorite(base_url, **conn_args):
    '''
       List favorite passwords.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#list_passwords
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      return the favorite passwords that the user has access to.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List favorite spasswords.')
    return tpmconn.collection('passwords/favorite.json')

def list_passwords_search(base_url, searchstring, exact_match = False, **conn_args):
    '''
       List passwords with searchstring.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#list_passwords
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/


       Args:
       base_url    : Your Team Password Manager URL
       searchstring: Search String
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      return the searchstring passwords that the user has access to.
      urlencode of the searchstring will be handled internally.

    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List all passwords with: %s' % searchstring)
    passwords = tpmconn.collection('passwords/search/%s.json' % quote_plus(searchstring))

    if exact_match == False:
       return passwords
    return _exact_match(passwords, 'name', searchstring)

def show_password(base_url, id, **conn_args):
    '''
       Show password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#show_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 200 OK with the results of the call in the response body.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Show password info: %s' % id)
    return tpmconn.get('passwords/%s.json' % id)

def list_user_access_on_password(base_url, id, **conn_args):
    '''
       List users who can access a password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#list_users_pwd
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      returns the effective permissions users have on a password.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List user access on password %s' % id)
    return tpmconn.collection('passwords/%s/security.json' % id)

def create_password(name, base_url, data, **conn_args):
    '''
       Create a password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#create_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       data        : The request body must include the data for the password. The required fields are the name and the id of the project the password.
                     {
                       "name": "Name of the password",
                       "project_id": 21,
                       "tags": (list of comma separated strings)
                       'access_info',
                       'username',
                       'email',
                       'password',
                       'expiry_date': (in ISO 8601 format: yyyy-mm-dd, or null or ''),
                       'notes',
                       'custom_data1', 'custom_data2' ... , 'custom_data10'
                     }
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 201 Created with the internal id of the password in the response body
    '''

    data['name'] = name
    tpmconn = TpmApi(base_url, conn_args)
    log.info('Create new password %s' % data)
    new_id = tpmconn.post('passwords.json', data).get('id')
    log.info('Password has been created with id %s' % new_id)
    return new_id

def update_password(name, base_url, id, data, **conn_args):
    '''
       Update a password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#update_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       data        : The request body must include the data for the password.
                     Only the fields that are included are updated, the other fields are left unchanged
                     {
                       'name': 'Name of the password',
                       'project_id': 21,
                       'tags': (list of comma separated strings)
                       'access_info',
                       'username': (in ISO 8601 format: yyyy-mm-dd, or null or ''),
                       'email',
                       'password',
                       'expiry_date'
                       'notes',
                       'custom_data1', 'custom_data2' ... , 'custom_data10'
                     }
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    data['name'] = name
    tpmconn = TpmApi(base_url, conn_args)
    log.info('Update Password %s with %s' % (id, data))
    tpmconn.put('passwords/%s.json' % id, data)

    return True

def update_security_of_password(base_url, id, data, **conn_args):
    '''
       Update security of a password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#update_security_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       data        : The request body must include the data for the password
                     managed_by:  It is the main manager of the password. If present, cannot be 0
                     users_permissions: It is an array of [user_id, permission_id]. User permissions will be set for the users passed
                                        permission_id can be: 0=no acces, 10=read, 20=edit data, 30=manage
                     groups_permissions: It is an array of [group_id, permission_id]. Groups permissions will be set for the groups passed
                                        permission_id can be: 0=no acces, 10=read, 20=edit data, 30=manage.
                     {
                       "managed_by": 1.
                       "users_permissions": [ [2,10],[3,20] ],
                       "groups_permissions": [ [1,20] ]
                     }
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Update security of password %s with %s' % (id, data))
    tpmconn.put('passwords/%s/security.json' % id, data)

    return True

def update_custom_fields_of_password(base_url, id, data, **conn_args):
    '''
       Update custom fields definitions of a password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#update_cf_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       data        : The request body must include the data for the password.
                     Only the fields that are included are updated, the other fields are left unchanged.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

                   {
                     "custom_label1": "MySQL user",
                     "custom_type1": "text",
                     "custom_label2": "MySQL password",
                     "custom_type2": "password",
                     ...
                   }

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Update custom fields of password %s with %s' % (id, data))
    tpmconn.put('passwords/%s/custom_fields.json' % id, data)

    return True

def delete_password(base_url, id, **conn_args):
    '''
       Delete a password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#delete_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Delete password %s' % id)
    tpmconn.delete('passwords/%s.json' % id)
    return True

def lock_password(base_url, id, **conn_args):
    '''
       Lock a password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#lock_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       id          : Internal id of the password
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Lock password %s' % id)
    tpmconn.put('passwords/%s/lock.json' % id)

    return True

def unlock_password(base_url, id, reason, **conn_args):
    '''
       Unlock a password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords/#unlock_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       reason      : Reason string to unlock the password. A notification will be sent to the password manager with the supplied reason
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Unlock password %s, Reason: %s' % (id, reason))
    tpmconn.unlock_reason = reason
    tpmconn.put('passwords/%s/unlock.json' % id)

    return True

def list_mypasswords(base_url, **conn_args):
    '''
       List my passwords.
       API Doc URL : https://teampasswordmanager.com/docs/api-my-passwords/#list_passwords
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      return the personal passwords of the user (My Passwords)
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List MyPasswords')
    return tpmconn.collection('my_passwords.json')

def list_mypasswords_search(base_url, searchstring, exact_match = False, **conn_args):
    '''
       List my passwords with searchstring.
       API Doc URL : https://teampasswordmanager.com/docs/api-my-passwords/#list_passwords
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       searchstring: Search String
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      return the searchstring passwords of the user (My Passwords)
      urlencode of the searchstring will be handled internally.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List MyPasswords with %s' % searchstring)
    mypasswords = tpmconn.collection('my_passwords/search/%s.json' % quote_plus(searchstring))

    if exact_match == False:
       return mypasswords
    return _exact_match(mypasswords, 'name', searchstring)

def show_mypassword(base_url, id, **conn_args):
    '''
       Show my password.
       API Doc URL : https://teampasswordmanager.com/docs/api-my-passwords/#show_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       id          : Internal id of the password
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       returns all the data of a password, identified by its internal id
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('Show MyPassword %s' % id)
    return tpmconn.get('my_passwords/%s.json' % id)

def create_mypassword(base_url, name, data, **conn_args):
    '''
       Create my password.
       API Doc URL : https://teampasswordmanager.com/docs/api-my-passwords/#create_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       data        : The request body must include the data for the password. The only required fields is the name of the password
                     {
                       'name': 'Name of the password',
                       'tags': 'list of comma separated strings'
                       'access_info',
                       'username',
                       'email',
                       'password',
                       'notes'
                     }
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 201 Created with the internal id of the password in the response body.
    '''

    data['name'] = name
    tpmconn = TpmApi(base_url, conn_args)
    log.info('Create MyPassword with %s' % data)
    new_id = tpmconn.post('my_passwords.json', data).get('id')
    log.info('MyPassword has been created with %s' % new_id)
    return new_id

def update_mypassword(base_url, id, data, **conn_args):
    '''
       Update my password.
       API Doc URL : https://teampasswordmanager.com/docs/api-my-passwords/#update_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       data        : The request body must include the data for the password. The only required fields is the name of the password
                     {
                       'name': 'Changed name of the password',
                       'tags': 'tag1,tag2,tag3',
                       'access_info': 'http:\/\/www.mywebsite.com\/admin',
                       'username': 'myuser',
                       'email': 'abc@abc.com',
                       'password': 'mypassword',
                       'notes': 'mynotes'
                     }

       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''


    tpmconn = TpmApi(base_url, conn_args)
    log.info('Update MyPassword %s with %s' % (id, data))
    tpmconn.put('my_passwords/%s.json' % id, data)

    return True

def delete_mypassword(base_url, id, **conn_args):
    '''
       Delete my password.
       API Doc URL : https://teampasswordmanager.com/docs/api-my-passwords/#delete_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Delete password %s' % id)
    tpmconn.delete('my_passwords/%s.json' % id)

    return True

def set_favorite_password(base_url, id, **conn_args):
    '''
       Set a password as favorite.
       API Doc URL : https://teampasswordmanager.com/docs/api-favorites/#set_fav
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.

    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Set password %s as favorite' % id)
    tpmconn.post('favorite_passwords/%s.json' % id)

    return True

def unset_favorite_password(base_url, id, **conn_args):
    '''
       Unset a password as favorite.
       API Doc URL : https://teampasswordmanager.com/docs/api-favorites/#del_fav
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the password
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

      If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Unset password %s as favorite' % id)
    tpmconn.delete('favorite_passwords/%s.json' % id)

    return True

def set_favorite_project(base_url, id, **conn_args):
    '''
       Set a project as favorite.
       API Doc URL : https://teampasswordmanager.com/docs/api-favorites/#set_fav
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Set project %s as favorite' % id)
    tpmconn.post('favorite_projects/%s.json' % id)

    return True

def unset_favorite_project(base_url, id, **conn_args):
    '''
       Unet a project as favorite.
       API Doc URL : https://teampasswordmanager.com/docs/api-favorites/#del_fav
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the project.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Unset project %s as favorite' % id)
    tpmconn.delete('favorite_projects/%s.json' % id)

    return True

def list_users(base_url, **conn_args):
    '''
       List users.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#list_users
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 200 OK with the results of the call in the response body.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List users')
    return tpmconn.collection('users.json')


def get_user_by(field, value, base_url, **conn_args):
    users = list_users(base_url, **conn_args)
    user = _exact_match(users, field, value)
    return user

def show_user(base_url, id, **conn_args):
    '''
       Show a user.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#show_user
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the user.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 200 OK with the results of the call in the response body.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('Show user %s' % id)
    return tpmconn.get('users/%s.json' % id)

def show_me(base_url, **conn_args):
    '''
       Show me.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#show_me
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 200 OK with the results of the call in the response body.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('Show Info about own user')
    return tpmconn.get('users/me.json')

def create_user(base_url, data, **conn_args):
    '''
       Create a User.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#create_user
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       data        : The request body must include the data for the user
                     {
                       "username": "johnnotboss",
                       "email_address": "john@test.com",
                       "name": "John",
                       "role": "admin" or "project manager" or "normal user" or "read only" or "only read",
                       "password": "testpassword"
                     }
                     One of these two fields MUST be used when creating a user:
                         'password': if this field is set, the user will be a normal (not LDAP) user.
                         'login_dn': if this field is set, the user will be an LDAP user (if LDAP is enabled).

                    * Note: if using version 6.68.138+, the LDAP server assigned is "Server 1".
                            With this version of the API other servers cannot be assigned.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 201 Created with the internal id of the user in the response body:
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Create user with %s' % data)
    new_id = tpmconn.post('users.json', data).get('id')
    log.info('User has been created with id %s' % new_id)
    return new_id

def update_user(base_url, id, data, **conn_args):
    '''
       Update a User.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#update_user
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the user.
       data        : The request body must include the data for the user.
                     Only the fields that are included are updated, the other fields are left unchanged.
                     {
                       "username": "johnnotboss",
                       "email_address": "john@test.com",
                       "name": "John",
                       "role": "admin" or "project manager" or "normal user" or "read only" or "only read",
                     }
                     * Note: the password of the user cannot be set by updating the user.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Update user %s with %s' % (id, data))
    tpmconn.put('users/%s.json' % id, data)

    return True

def change_user_password(base_url, id, data, **conn_args):
    '''
       Change password of a User.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#change_password
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the user.
       data        : The data must include new password for the user.
                     {
                       "password": "thisistheone"
                     }
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Change user %s password' % id)
    tpmconn.put('users/%s/change_password.json' % id, data)

    return True

def activate_user(base_url, id, **conn_args):
    '''
       Activate a User.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#activate_deactivate
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       id          : Internal id of the user.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Activate user %s' % id)
    tpmconn.put('users/%s/activate.json' % id)

    return True

def deactivate_user(base_url, id, **conn_args):
    '''
       Dectivate a User.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#activate_deactivate
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the user.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Deactivate user %s' % id)
    tpmconn.put('users/%s/deactivate.json' % id)

    return True

def convert_user_to_ldap(base_url, id, DN, **conn_args):
    '''
       Convert a normal user to a LDAP user.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#convert_to_ldap
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the user.
       DN          : The request body must include the 'login_dn' for the user
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    data = {'login_dn': DN}
    log.info('Convert User %s to LDAP DN %s' % (id, DN))
    tpmconn.put('users/%s/convert_to_ldap.json' % id, data)

    return True

def convert_ldap_user_to_normal(base_url, id, **conn_args):
    '''
       Convert a LDAP user to a normal user.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#convert_to_ldap
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the user.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Convert User %s from LDAP to normal user' % id)
    tpmconn.put('users/%s/convert_to_normal.json' % id)

    return True

def delete_user(base_url, id, **conn_args):
    '''
       Delete a user.
       API Doc URL : https://teampasswordmanager.com/docs/api-users/#delete_user
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the user.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Delete user %s' % id)
    tpmconn.delete('users/%s.json' % id)

    return True

def list_groups(base_url, **conn_args):
    '''
       List Groups.
       API Doc URL : https://teampasswordmanager.com/docs/api-groups/#list_groups
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 200 OK with the results of the call in the response body.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('List groups')
    return tpmconn.collection('groups.json')

def get_group_by(field, value, base_url, **conn_args):
    groups = list_groups(base_url, **conn_args)
    group  = _exact_match(groups, field, value)
    return group

def show_group(base_url, id, **conn_args):
    '''
       Show a Group.
       API Doc URL : https://teampasswordmanager.com/docs/api-groups/#show_group
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the group.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 200 OK with the results of the call in the response body.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('Show group %s' % id)
    return tpmconn.get('groups/%s.json' % id)

def create_group(base_url, name, **conn_args):
    '''
       Create a Group.
       API Doc URL : https://teampasswordmanager.com/docs/api-groups/#create_group
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       data        : Data must include the name for the group (which is the only field that can be set in a group):
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 201 Created with the internal id of the group in the response body:
    '''
    data = {}
    data['name'] = name
    tpmconn = TpmApi(base_url, conn_args)
    log.info('Create group with %s' % data)
    new_id = tpmconn.post('groups.json', data).get('id')
    log.info('Group has been created with id %s' % new_id)
    return new_id

def update_group(base_url, id, new_name, **conn_args):
    '''
       Update a Group.
       API Doc URL : https://teampasswordmanager.com/docs/api-groups/#update_group
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the group.
       data        : Data must include the name for the group (which is the only field to be updated)
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    data = {}
    data['name'] = new_name
    tpmconn = TpmApi(base_url, conn_args)
    log.info('Update group %s with %s' % (id, data))
    tpmconn.put('groups/%s.json' % id, data)

    return True

def add_user_to_group(base_url, group_id, user_id, **conn_args):
    '''
       Add a user to a group.
       API Doc URL : https://teampasswordmanager.com/docs/api-groups/#add_user
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       group_id     : Internal id of the group.
       user_id      : Internal id of the user.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Add User %s to Group %s' % (user_id, group_id))
    tpmconn.put('groups/%s/add_user/%s.json' % (group_id, user_id))

    return True

def delete_user_from_group(base_url, group_id, user_id, **conn_args):
    '''
       Delete a user from a group.
       API Doc URL : https://teampasswordmanager.com/docs/api-groups/#del_user
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       group_id     : Internal id of the group.
       user_id      : Internal id of the user.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Delete user %s from group %s' % (user_id, group_id))
    tpmconn.put('groups/%s/delete_user/%s.json' % (group_id, user_id))

    return True

def delete_group(base_url, id, **conn_args):
    '''
       Delete a group.
       API Doc URL : https://teampasswordmanager.com/docs/api-groups/#delete_group
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    : Your Team Password Manager URL
       id          : Internal id of the group.
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 204 No content and the response body is empty.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.info('Delete group %s' % id)
    tpmconn.delete('groups/%s.json' % id)

    return True

def generate_password(base_url, **conn_args):
    '''
       Generate a new random password.
       API Doc URL : https://teampasswordmanager.com/docs/api-passwords-generator/
       Auth Doc URL: https://teampasswordmanager.com/docs/api-authentication/

       Args:
       base_url    :  Your Team Password Manager URL
       **conn_args : (Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                     (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

       If successful, the response code is 200 OK with the generated password in the response body.
    '''

    tpmconn = TpmApi(base_url, conn_args)
    log.debug('Generate new password')
    return tpmconn.get('generate_password.json')
