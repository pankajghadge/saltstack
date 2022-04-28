# -*- coding: utf-8 -*-
"""
    :maturity:      develop
    :platform:      team password manager
    :developer:     Pankaj Ghadge
"""

# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals

# Import Salt libs
import salt.utils.json

# Import 3rd-party libs
from salt.ext import six
import logging
log = logging.getLogger(__name__)


# set up virtual function
def __virtual__():
    """
    Only load if the bigip exec module is available in __salt__
    """
    if "teampass.list_projects" in __salt__:
        return "teampass"
    return (False, "Team password manager (teampass) module could not be loaded")

def _test_output(ret, action, entity):
    """
    For testing just output what the state will attempt to do without actually doing it.
    """

    if action == "create" or action == "add":
        ret["comment"] += "The create action will attempt to create a " + entity + " in TPM if it does not already exist.\n"
    elif action == "delete":
        ret["comment"] += "The delete action will attempt to delete a " + entity + " from TPM if it exists.\n"
    elif action == "change":
        ret["comment"] += ("The change action will change the passed value in TPM if it exist.\n")
    elif action == "update":
        ret["comment"] += "The update action will attempt to "+  entity +" in TPM only if it exists.\n"
    elif action == "archive" or action == "unarchive":
        ret["comment"] += "The action will attempt to "+ action +" an existing "+ entity +" from TPM if it exists.\n"
    elif action == "favorite" or action == "unfavorite":
        ret["comment"] += "The action will set a "+ entity +" as "+  action +" in TPM if it exists.\n"

    ret["changes"] = {}
    ret["result"] = None

    return ret

def _load_result(ret, error, value =""):
    if error == "Permission":
       ret["comment"] = "Wrong permission: Permission values must be -1, 0, 10, 20, 30, 40, 50, 60, or 99 in TPM"
    elif error == "Project":
       ret["comment"] = "Wrong project: Project name "+ value +" does not exists in TPM"
    elif error == "Group":
       ret["comment"] = "Wrong Group: Group name "+ value +" does not exists in TPM"
    elif error == "User":
       ret["comment"] = "Wrong User: User name "+ value +" does not exists in TPM"
    elif error == "Password":
       ret["comment"] = "Wrong Password: Password name "+ value +" does not exists in TPM"

    return ret

def _check_tpm_permission(permission, item):
    """
      Project: permission_id can be:
      -1 - (Do not set): set permissions for individual users/groups, not globally.
       0 - No access: the user/group cannot access the project or any of its passwords.
      10 - Traverse: the user/group can see the project name only.
      20 - Read: the user/group can only read project data and its passwords.
      30 - Read / Create passwords: the user/group can read project data and create passwords in it.
      40 - Read / Edit passwords data: the user/group can read project data and edit the data of its passwords (and also create passwords).
      50 - Read / Manage passwords: the user/group can read project data and manage its passwords (and also create passwords).
      60 - Manage: the user/group has total control over the project and its passwords.
      99 - Inherit from parent: the user/group will inherit the permission set on the parent project. Cannot be set if the project is a root project.

      Password :
      permission_id can be: 0=no acces, 10=read, 20=edit data, 30=manage

    """
    tpm_permissions = []
    if item == 'project':
       tpm_permissions = [-1, 0, 10, 20, 30, 40, 50, 60, 99]
    elif item == 'password':
       tpm_permissions = [0, 10, 20, 30]

    if isinstance(permission,list):
       permission = list(set(permission))
       if(set(permission).issubset(set(tpm_permissions))):
          return True
    elif isinstance(permission,int) and (permission in tpm_permissions):
          return True
    return False

def _get_users_permissions_ids(users_permissions, base_url, field = "name", **conn_args):
    users = __salt__["teampass.list_users"](base_url, **conn_args)
    users_match = list(filter(lambda user: user["name"] in users_permissions.keys(), users))

    users_permissions_list = []

    for i, user in enumerate(users_match):
        users_permissions_list.append([users_match[i]["id"], users_permissions[users_match[i][field]]])

    #users_permissions_dict = dict((users_match[key], value) for (key, value) in users_permissions.items())

    return users_permissions_list


def _get_groups_permissions_ids(groups_permissions, base_url, field = "name", **conn_args):
    groups = __salt__["teampass.list_groups"](base_url, **conn_args)
    groups_match = list(filter(lambda group: group["name"] in groups_permissions.keys(), groups))

    groups_permissions_list = []

    for i, group in enumerate(groups_match):
        groups_permissions_list.append([groups_match[i]["id"], groups_permissions[groups_match[i][field]]])

    return groups_permissions_list

def create_project(name, base_url, data, **conn_args):

    """
    Create a new project in TPM if it does not already exist.
    name
        The name of the project to create
    base_url
        The host/address of the TPM
    Data : The request body must include the data for the project.
           Only the fields that are included are updated, the other fields are left unchanged
          {
            "name": "Name of the project",
            "tags": "tag1,tag2,tag3",
            "notes": "some notes"
          }
    **conn_args :(Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                 (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

    """

    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "create", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    if 'parent' in data:
        search_parent_project = __salt__["teampass.list_projects_search"](base_url, data['parent'], exact_match = True, **conn_args)
        if len(search_parent_project) == 1:
           project             = search_parent_project[0]
           data['parent_id']   = project['id']
           del data['parent']
        else:
           ret["result"] = False
           ret["comment"] = "Parent Project does not exists. Please enter the right parent project name in salt state"
           return ret

    if not search:
       new_id = __salt__["teampass.create_project"](name, base_url, data, **conn_args)
       if new_id:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "Project id " + str(new_id)
          ret["comment"] = "Project was successfully created."

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "A Project by this name currently exists.  No action taken"

    return ret

def update_project(name, base_url, data, **conn_args):

    """
    Create a new project in TPM if it does not already exist.
    name
        The name of the project to create
    base_url
        The host/address of the TPM
    Data : The request body must include the data for the project.
           Only the fields that are included are updated, the other fields are left unchanged
          {
            "name": "Name of the project",
            "tags": "tag1,tag2,tag3",
            "notes": "some notes"
          }
    **conn_args :(Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                 (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

    """

    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "update", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       project      = search[0]
       project_id   = project['id']
       project_name = project['name']

       flag = __salt__["teampass.update_project"](project_name, base_url, project_id, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "Project updated successfully"
          ret["comment"] = "Project was successfully updated."

    # else something else was returned
    else:
        ret["comment"] = "A Project with this name was not found."

    return ret

def change_parent_of_project(name, base_url, new_parent, **conn_args):
    """
    Create a new project in TPM if it does not already exist.
    name
        The name of the project to create
    base_url
        The host/address of the TPM
    Data : The request body must include the data for the project.
           Only the fields that are included are updated, the other fields are left unchanged
          {
            "name": "Name of the project",
            "tags": "tag1,tag2,tag3",
            "notes": "some notes"
          }
    **conn_args :(Method: 1)  For HTTP Basic Authentication pass conn_args as username and password
                 (Method: 2)  For HMAC Authentication pass conn_args as private_key and public_key

    """

    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "change", "project" )


    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    # is this project currently configured?
    new_parent = __salt__["teampass.list_projects_search"](base_url, new_parent, exact_match = True, **conn_args)

    # This project already has the requested parent

    if len(search) == 1 and len(new_parent) == 1:
         project      = search[0]
         project_id   = project['id']

         current_project = __salt__["teampass.show_project"](base_url, project_id, **conn_args)
         parent_id       = current_project['parent_id']

         new_project      = new_parent[0]
         new_project_id   = new_project['id']

         if parent_id != new_project_id:

            flag = __salt__["teampass.change_parent_of_project"](base_url, project_id, new_project_id, **conn_args)
            if flag:
               ret["result"] = True
               ret["changes"]["new"] = "Project parent id changed successfully to " + str(new_project_id)
               ret["comment"] = "Project parent id was successfully changed."
         else:
               ret["result"] = True
               ret["comment"] = "This project already has the requested parent"
    else:
          ret["comment"] = "Parent details with this name was not found."

    return ret

def update_security_of_project(name, base_url, data, **conn_args):

    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if "users_permissions" in data:
       users_permissions = _get_users_permissions_ids(data["users_permissions"], base_url, **conn_args)
       if not _check_tpm_permission(list(data["users_permissions"].values()), 'project'):
          ret = _load_result(ret, 'Permissions')
          return ret
       data["users_permissions"] = users_permissions

    if "groups_permissions" in data:
       groups_permissions = _get_groups_permissions_ids(data["groups_permissions"], base_url, **conn_args)
       if not _check_tpm_permission(list(data["groups_permissions"].values()), 'project'):
          ret = _load_result(ret, 'Permissions')
          return ret
       data["groups_permissions"] = groups_permissions

    if "managed_by" in data:
       retrieved_user = __salt__["teampass.get_user_by"]("name", data["managed_by"], base_url, **conn_args)
       if len(retrieved_user) != 1:
          ret = _load_result(ret, 'User', data["managed_by"])
          return ret

       data["managed_by"] = retrieved_user[0]["id"]

    if __opts__["test"]:
       return _test_output( ret, "update", "update security of project" )

    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       project      = search[0]
       project_id   = project['id']
       project_name = project['name']

       data = __salt__["teampass.update_security_of_project"](base_url, project_id, data, **conn_args)

       if data:
          ret["result"] = True
          ret["changes"]["new"] = "Security of project updated"
          ret["comment"] = "Security of project updated successfully"

    # else something else was returned
    else:
        ret["comment"] = "A Project with this name was not found."

    return ret

def archive_project(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "archive", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       project      = search[0]
       project_id   = project['id']
       project_name = project['name']

       current_project = __salt__["teampass.show_project"](base_url, project_id, **conn_args)
       is_archived     = current_project['archived']

       if not is_archived:
          flag = __salt__["teampass.archive_project"](base_url, project_id, **conn_args)

          if flag:
             ret["result"] = True
             ret["changes"]["new"] = "Project archived successfully"
             ret["comment"] = "Project archived successfully"
          else:
             ret["comment"] = "Failed to archive project"
       else:
          ret["result"]  = True
          ret["comment"] = "This project is already archived"
    # else something else was returned
    else:
       ret["comment"] = "A Project with this name was not found."


    return ret

def unarchive_project(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "unarchive", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       project      = search[0]
       project_id   = project['id']
       project_name = project['name']

       current_project = __salt__["teampass.show_project"](base_url, project_id, **conn_args)
       is_archived     = current_project['archived']

       if is_archived:
          flag = __salt__["teampass.unarchive_project"](base_url, project_id, **conn_args)

          if flag:
             ret["result"] = True
             ret["changes"]["new"] = "Project unarchived successfully"
             ret["comment"] = "Project unarchived successfully"
          else:
             ret["comment"] = "Failed to unarchive project"
       else:
          ret["result"]  = True
          ret["comment"] = "This project is already unarchived"


    # else something else was returned
    else:
       ret["comment"] = "A Project with this name was not found."


    return ret

def delete_project(name, base_url, **conn_args):

    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "delete", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       project      = search[0]
       project_id   = project['id']
       project_name = project['name']

       current_project = __salt__["teampass.show_project"](base_url, project_id, **conn_args)
       is_leaf         = current_project['is_leaf']

       if is_leaf:
          flag = __salt__["teampass.delete_project"](base_url, project_id, **conn_args)

          if flag:
             ret["result"] = True
             ret["comment"] = "Project deleted successfully"
          else:
             ret["comment"] = "Failed to delete the project"
       else:
          ret["result"]  = False
          ret["comment"] = "This project is not a leaf node, only leaf projects can be deleted"

    # else something else was returned
    else:
       ret["comment"] = "A Project with this name was not found."

    return ret

def set_favorite_project(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "unarchive", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       project      = search[0]
       project_id   = project['id']
       project_name = project['name']

       favorite_projects = __salt__["teampass.list_projects_favorite"](base_url, **conn_args)
       is_favorite = list(filter(lambda favorite_project: project_name == favorite_project['name'] , favorite_projects))

       if len(is_favorite) == 0:
          flag = __salt__["teampass.set_favorite_project"](base_url, project_id, **conn_args)

          if flag:
             ret["result"] = True
             ret["changes"]["new"] = "Successfully added the project to favorite list"
             ret["comment"] = "Successfully added the project to favorite list"
          else:
             ret["comment"] = "Failed to set project as favorite"
       else:
          ret["result"] = True
          ret["comment"] = "Project already added to favorite list"


    # else something else was returned
    else:
       ret["comment"] = "A Project with this name was not found."

    return ret

def unset_favorite_project(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "unarchive", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_projects_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       project      = search[0]
       project_id   = project['id']
       project_name = project['name']

       favorite_projects = __salt__["teampass.list_projects_favorite"](base_url, **conn_args)
       is_favorite = list(filter(lambda favorite_project: project_name == favorite_project['name'] , favorite_projects))

       if len(is_favorite) == 1:

          flag = __salt__["teampass.unset_favorite_project"](base_url, project_id, **conn_args)

          if flag:
             ret["result"] = True
             ret["changes"]["new"] = "Successfully unset the favorite project"
             ret["comment"] = "Successfully unset the favorite project"
          else:
             ret["comment"] = "Failed to unset the favorite project"
       else:
          ret["result"] = True
          ret["comment"] = "Project not found in a favorite list. No action taken"

    # else something else was returned
    else:
       ret["comment"] = "A Project with this name was not found."

    return ret

def create_password(name, base_url, project, data, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    project_search = __salt__["teampass.list_projects_search"](base_url, project, exact_match = True, **conn_args)

    if len(project_search) == 0:
       ret["comment"] = "Project with this name does not exists in TPM"
       return ret

    data['project_id']  = project_search[0]['id']

    if __opts__["test"]:
       return _test_output( ret, "create", "password" )

    # is this project currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 0:
       new_id = __salt__["teampass.create_password"](name, base_url, data, **conn_args)
       if new_id:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = " Password has been created with id " + str(new_id)
          ret["comment"] = "Password was successfully created."

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "This password already exists in this project. No action taken"

    return ret

def update_password(name, base_url, project, data, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    project_search = __salt__["teampass.list_projects_search"](base_url, project, exact_match = True, **conn_args)

    if len(project_search) == 0:
       ret["comment"] = "Project with this name does not exists in TPM"
       return ret

    if __opts__["test"]:
       return _test_output( ret, "create", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 1:
       password      = is_duplicate[0]
       password_id   = password['id']
       password_name = password['name']

       flag = __salt__["teampass.update_password"](password_name, base_url, password_id, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "Password updated successfully"
          ret["comment"] = "Project was successfully created."

    # else something else was returned
    else:
        ret["comment"] = "A Project with this name was not found."

    return ret

def update_security_of_password(name, base_url, project, data, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    project_search = __salt__["teampass.list_projects_search"](base_url, project, exact_match = True, **conn_args)

    if len(project_search) == 0:
       ret["comment"] = "Project with this name does not exists in TPM"
       return ret

    if "users_permissions" in data:
       users_permissions = _get_users_permissions_ids(data["users_permissions"], base_url, **conn_args)
       if not _check_tpm_permission(list(data["users_permissions"].values()), 'password'):
          ret = _load_result(ret, 'Permissions')
          return ret
       data["users_permissions"] = users_permissions

    if "groups_permissions" in data:
       groups_permissions = _get_groups_permissions_ids(data["groups_permissions"], base_url, **conn_args)
       if not _check_tpm_permission(list(data["groups_permissions"].values()), 'password'):
          ret = _load_result(ret, 'Permissions')
          return ret
       data["groups_permissions"] = groups_permissions

    if "managed_by" in data:
       retrieved_user = __salt__["teampass.get_user_by"]("name", data["managed_by"], base_url, **conn_args)
       if len(retrieved_user) != 1:
          ret = _load_result(ret, 'User', data["managed_by"])
          return ret

       data["managed_by"] = retrieved_user[0]["id"]

    if __opts__["test"]:
       return _test_output( ret, "update", "update security of password")

    # is this project and password currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 1:
       password      = is_duplicate[0]
       password_id   = password['id']
       password_name = password['name']

       flag = __salt__["teampass.update_security_of_password"](base_url, password_id, data, **conn_args)

       if flag:
          ret["result"] = True
          ret["changes"]["new"] = "Security of password updateed"
          ret["comment"] = "Security of password updateed successfully"

    # else something else was returned
    else:
        ret["comment"] = "A password with this name was not found."

    return ret

def update_custom_fields_of_password(name, base_url, project, data, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    project_search = __salt__["teampass.list_projects_search"](base_url, project, exact_match = True, **conn_args)

    if len(project_search) == 0:
       ret["comment"] = "Project with this name does not exists in TPM"
       return ret

    if __opts__["test"]:
       return _test_output( ret, "update", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 1:
       password      = is_duplicate[0]
       password_id   = password['id']
       password_name = password['name']

       flag = __salt__["teampass.update_custom_fields_of_password"](base_url, password_id, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "Updated password custom fields successfully"
          ret["comment"] = "Project was successfully created."

    # else something else was returned
    else:
        ret["comment"] = "A Password with this name was not found."

    return ret

def delete_password(name, project, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "delete", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 1:
       password      = is_duplicate[0]
       password_id   = password['id']
       password_name = password['name']

       flag = __salt__["teampass.delete_password"](base_url, password_id, **conn_args)

       if flag:
          ret["result"] = True
          ret["comment"] = "Password deleted successfully"
       else:
          ret["comment"] = "Failed to delete the password"

    # else something else was returned
    else:
       ret["comment"] = "A Password with this name was not found."

    return ret

def lock_password(name, project, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "delete", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 1:
       password      = is_duplicate[0]
       password_id   = password['id']
       password_name = password['name']

       current_password = __salt__["teampass.show_password"](base_url, password_id, **conn_args)
       if current_password['locked']:
          ret["result"] = True
          ret["comment"] = "The password is already locked. No action taken"
          return ret

       flag = __salt__["teampass.lock_password"](base_url, password_id, **conn_args)

       if flag:
          ret["result"] = True
          ret["comment"] = "Password locked successfully"
       else:
          ret["comment"] = "Failed to lock the password"

    # else something else was returned
    else:
       ret["comment"] = "A Password with this name was not found."

    return ret

def unlock_password(name, project, base_url, reason, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "delete", "project" )

    # is this project currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 1:
       password      = is_duplicate[0]
       password_id   = password['id']
       password_name = password['name']

       current_password = __salt__["teampass.show_password"](base_url, password_id, **conn_args)
       if not current_password['locked']:
          ret["result"] = True
          ret["comment"] = "The password is already unlocked. No action taken"
          return ret

       flag = __salt__["teampass.unlock_password"](base_url, password_id, reason, **conn_args)

       if flag:
          ret["result"] = True
          ret["comment"] = "Password unlocked successfully"
       else:
          ret["comment"] = "Failed to unlock the password"

    # else something else was returned
    else:
       ret["comment"] = "A Password with this name was not found."

    return ret

def create_mypassword(name, base_url, data, **conn_args):

    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "create", "mypassword" )

    # is this mypassword currently configured?
    search = __salt__["teampass.list_mypasswords_search"](base_url, name, exact_match = True, **conn_args)

    if len(search)==0:
       new_id = __salt__["teampass.create_mypassword"](base_url, name, data, **conn_args)
       if new_id:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = " MyPassword has been created with id " + str(new_id)
          ret["comment"] = "MyPassword was successfully created."

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "My Password by this name currently exists.  No action taken"

    return ret


def update_mypassword(name, base_url, data, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "create", "project" )

    # is this mypassword currently configured?
    search = __salt__["teampass.list_mypasswords_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       password      = search[0]
       password_id   = password['id']
       password_name = password['name']

       flag = __salt__["teampass.update_mypassword"](base_url, password_id, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "MyPassword updated successfully"
          ret["comment"] = "MyPassword was successfully updated."

    # else something else was returned
    else:
        ret["comment"] = "A Project with this name was not found."

    return ret

def delete_mypassword(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "delete", "MyPassword" )

    # is this mypassword currently configured?
    search = __salt__["teampass.list_mypasswords_search"](base_url, name, exact_match = True, **conn_args)

    if len(search) == 1:
       password      = search[0]
       password_id   = password['id']
       password_name = password['name']

       flag = __salt__["teampass.delete_mypassword"](base_url, password_id, **conn_args)

       if flag:
          ret["result"] = True
          ret["comment"] = "MyPassword deleted successfully"
       else:
          ret["comment"] = "Failed to delete the Mypassword"

    # else something else was returned
    else:
       ret["comment"] = "MyPassword with this name was not found."

    return ret

def set_favorite_password(name, project, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "unset", "favorite password" )

    # is this password and project currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 1:
       password      = search[0]
       password_id   = password['id']
       password_name = password['name']

       current_password = __salt__["teampass.show_password"](base_url, password_id, **conn_args)
       if current_password['favorite']:
          ret["result"] = True
          ret["comment"] = "The password is already added to favorite list. No action taken"
          return ret


       flag = __salt__["teampass.set_favorite_password"](base_url, password_id, **conn_args)

       if flag:
          ret["result"] = True
          ret["comment"] = "Successfully set the favorite password"
       else:
          ret["comment"] = "Failed to set the favorite password"

    # else something else was returned
    else:
       ret["comment"] = "A Password with this name was not found."

    return ret

def unset_favorite_password(name, project, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "unset", "favorite password" )

    # is this password and project currently configured?
    search = __salt__["teampass.list_passwords_search"](base_url, name, exact_match = True, **conn_args)
    is_duplicate = list(filter(lambda password: project == password['project']['name'] and name == password['name'], search))

    if len(is_duplicate) == 1:
       password      = search[0]
       password_id   = password['id']
       password_name = password['name']

       current_password = __salt__["teampass.show_password"](base_url, password_id, **conn_args)
       if not current_password['favorite']:
          ret["result"] = True
          ret["comment"] = "The password not found in favorite list. No action taken"
          return ret

       flag = __salt__["teampass.unset_favorite_password"](base_url, password_id, **conn_args)

       if flag:
          ret["result"] = True
          ret["comment"] = "Successfully unset the favorite password"
       else:
          ret["comment"] = "Failed to unset the favorite password"

    # else something else was returned
    else:
       ret["comment"] = "A Password with this name was not found."

    return ret

def create_user(name, base_url, data, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "create", "user" )

    # is this user currently configured?
    retrieved_user = __salt__["teampass.get_user_by"]("name", name, base_url, **conn_args)
    #users = __salt__["teampass.list_users"](base_url, **conn_args)
    #retrieved_user = filter(lambda user: name in user['name'] , users)

    if len(retrieved_user) == 0:
       new_id = __salt__["teampass.create_user"](name, base_url, data, **conn_args)
       if new_id:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "User has been created with id " + str(new_id)
          ret["comment"] = "User was successfully created."

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "A User by this name currently exists. No action taken"

    return ret

def update_user(name, base_url, data, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "update", "user" )

    # is this user currently configured?
    #users = __salt__["teampass.list_users"](base_url, **conn_args)
    #retrieved_users = filter(lambda user: name in user['name'] , users)

    retrieved_user = __salt__["teampass.get_user_by"]("name", name, base_url, **conn_args)

    if len(retrieved_user) == 1:
       user      = retrieved_user[0]
       user_id   = user['id']
       user_name = user['name']

       flag = __salt__["teampass.update_user"](user_name, user_id, base_url, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "User updated successfully"
          ret["comment"] = "User was successfully updated."

    # else something else was returned
    else:
        ret["comment"] = "A User with this name was not found."

    return ret


def change_user_password(name, base_url, data, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "change", "user password" )

    # is this user currently configured?
    #users = __salt__["teampass.list_users"](base_url, **conn_args)
    #retrieved_user = filter(lambda user: name in user['name'] , users)

    retrieved_user = __salt__["teampass.get_user_by"]("name", name, base_url, **conn_args)

    if len(retrieved_user) == 1:
       user      = retrieved_user[0]
       user_id   = user['id']
       user_name = user['name']

       flag = __salt__["teampass.change_user_password"](user_name, user_id, base_url, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "User Password updated successfully"
          ret["comment"] = "User Password was successfully updated."

    # else something else was returned
    else:
        ret["comment"] = "A User with this name was not found."

    return ret

def activate_user(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "activate", "user" )

    # is this user currently configured?
    #users = __salt__["teampass.list_users"](base_url, **conn_args)
    #retrieved_users = filter(lambda user: name in user['name'] , users)

    retrieved_user = __salt__["teampass.get_user_by"]("name", name, base_url, **conn_args)

    if len(retrieved_user) == 1:
       user      = retrieved_user[0]
       user_id   = user['id']
       user_name = user['name']

       flag = __salt__["teampass.activate_user"](user_name, user_id, base_url, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "User activated successfully"
          ret["comment"] = "User activatation was successfully"

    # else something else was returned
    else:
        ret["comment"] = "A User with this name was not found."

    return ret

def deactivate_user(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "deactivate", "user" )

    # is this user currently configured?
    #users = __salt__["teampass.list_users"](base_url, **conn_args)
    #retrieved_users = filter(lambda user: name in user['name'] , users)

    retrieved_user = __salt__["teampass.get_user_by"]("name", name, base_url, **conn_args)

    if len(retrieved_user) == 1:
       user      = retrieved_user[0]
       user_id   = user['id']
       user_name = user['name']

       flag = __salt__["teampass.deactivate_user"](user_name, user_id, base_url, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "User deactivated successfully"
          ret["comment"] = "User deactivatation was successfully"

    # else something else was returned
    else:
        ret["comment"] = "A User with this name was not found."

    return ret

def delete_user(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "change", "user password" )

    # is this user currently configured?
    #users = __salt__["teampass.list_users"](base_url, **conn_args)
    #retrieved_users = filter(lambda user: name in user['name'] , users)

    retrieved_user = __salt__["teampass.get_user_by"]("name", name, base_url, **conn_args)

    if len(retrieved_user) == 1:
       user      = retrieved_user[0]
       user_id   = user['id']
       user_name = user['name']

       flag = __salt__["teampass.delete_user"](user_name, user_id, base_url, data, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "User deleted successfully"
          ret["comment"] = "User deleted successfully"

    # else something else was returned
    else:
        ret["comment"] = "A User with this name was not found."

    return ret

def create_group(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "create", "group" )

    # is this user currently configured?
    #groups = __salt__["teampass.list_groups"](base_url, **conn_args)
    #retrieved_groups = filter(lambda group: name in group['name'] , groups)

    retrieved_group = __salt__["teampass.get_group_by"]("name", name, base_url, **conn_args)

    if len(retrieved_group) == 0:
       new_id = __salt__["teampass.create_group"](base_url, name, **conn_args)
       if len(new_id):
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "Groups has been created with id " + str(new_id)
          ret["comment"] = "Group was successfully created."

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "A Group by this name currently exists. No action taken"

    return ret

def update_group(name, base_url, new_name, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "update", "group" )

    # is this user currently configured?
    #groups = __salt__["teampass.list_groups"](base_url, **conn_args)
    #retrieved_groups = filter(lambda group: name in group['name'] , groups)

    retrieved_group = __salt__["teampass.get_group_by"]("name", name, base_url, **conn_args)

    if len(retrieved_group) == 1:
       group      = retrieved_group[0]
       group_id   = group['id']
       group_name = group['name']

       flag = __salt__["teampass.update_group"](base_url, group_id, new_name, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "Groups has been created with id " + str(new_id)
          ret["comment"] = "Group was successfully created."

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "A Group by this name was not found."

    return ret

def add_user_to_group(name, group_name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "add", " user to group" )

    # is this user currently configured?
    #users = __salt__["teampass.list_users"](base_url, **conn_args)
    #retrieved_users = filter(lambda user: name in user['name'] , users)

    retrieved_user = __salt__["teampass.get_user_by"]("name", name, base_url, **conn_args)

    # is this group currently configured?
    #groups = __salt__["teampass.list_groups"](base_url, **conn_args)
    #retrieved_groups = filter(lambda group: group_name in group['name'] , groups)

    retrieved_group = __salt__["teampass.get_group_by"]("name", group_name, base_url, **conn_args)

    if len(retrieved_group) == 1 and len(retrieved_user) == 1:
       user      = retrieved_user[0]
       user_id   = user['id']
       user_name = user['name']

       group      = retrieved_group[0]
       group_id   = group['id']
       group_name = group['name']

       flag = __salt__["teampass.add_user_to_group"](base_url, group_id, user_id, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "User has been successfully added to group " + group_name
          ret["comment"] = "User added successfully to Group."

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "A User or Group by this name was not found."

    return ret

def delete_user_from_group(name, group_name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__["test"]:
       return _test_output( ret, "add", " user to group" )

    # is this user currently configured?
    #users = __salt__["teampass.list_users"](base_url, **conn_args)
    #retrieved_users = filter(lambda user: name in user['name'] , users)

    retrieved_user = __salt__["teampass.get_user_by"]("name", name, base_url, **conn_args)

    # is this group currently configured?
    #groups = __salt__["teampass.list_groups"](base_url, **conn_args)
    #retrieved_groups = filter(lambda group: group_name in group['name'] , groups)

    retrieved_group = __salt__["teampass.get_group_by"]("name", group_name, base_url, **conn_args)

    if len(retrieved_group) == 1 and len(retrieved_user) == 1:
       user      = retrieved_user[0]
       user_id   = user['id']
       user_name = user['name']

       group      = retrieved_group[0]
       group_id   = group['id']
       group_name = group['name']

       flag = __salt__["teampass.delete_user_from_group"](base_url, group_id, user_id, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "User has been successfully deleted from group " + group_name
          ret["comment"] = "User deleted successfully from Group."

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "A User or Group by this name was not found."

    return ret

def delete_group(name, base_url, **conn_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if __opts__["test"]:
       return _test_output( ret, "update", "group" )

    # is this user currently configured?
    #groups = __salt__["teampass.list_groups"](base_url, **conn_args)
    #retrieved_groups = filter(lambda group: name in group['name'] , groups)

    retrieved_group = __salt__["teampass.get_group_by"]("name", name, base_url, **conn_args)

    if len(retrieved_group) == 1:
       group      = retrieved_group[0]
       group_id   = group['id']
       group_name = group['name']

       flag = __salt__["teampass.delete_group"](base_url, group_id, **conn_args)
       if flag:
          ret["result"] = True
          ret["changes"]["old"] = {}
          ret["changes"]["new"] = "Groups has been deleted successfully"
          ret["comment"] = "Group deleted successfully"

    # else something else was returned
    else:
        ret["result"] = True
        ret["comment"] = "A Group by this name was not found."

    return ret
