# -*- coding: utf-8 -*-
"""
    :Maturity  :      develop
    :Platform  :      Zabbix maintenance
    :Developer :      Pankaj Ghadge
"""

from __future__ import absolute_import, print_function, unicode_literals

try:
  import logging
  import os
  import socket
  import urllib.error
  import datetime
  import time

  import salt.utils.data
  import salt.utils.files
  import salt.utils.http
  import salt.utils.json
  from salt.exceptions import SaltException
  from salt.utils.versions import LooseVersion as _LooseVersion
  log = logging.getLogger(__name__)
  HAS_LIBS = True
except ImportError:
  HAS_LIBS = False


__virtualname__ = 'zabbix_maintenance'

def __virtual__():
    '''
    Load only if requests module is installed
    '''
    if HAS_LIBS:
        return __virtualname__
    return (False, 'zabbix_maintenance module cannot be loaded: some python libraries are not available.')


def _query(method, params, url, auth=None):
    """
    JSON request to Zabbix API.
    .. versionadded:: 2016.3.0
    :param method: actual operation to perform via the API
    :param params: parameters required for specific method
    :param url: url of zabbix api
    :param auth: auth token for zabbix api (only for methods with required authentication)
    :return: Response from API with desired data in JSON format. In case of error returns more specific description.
    .. versionchanged:: 2017.7
    """

    unauthenticated_methods = [
        "user.login",
        "apiinfo.version",
    ]

    header_dict = {"Content-type": "application/json"}
    data = {"jsonrpc": "2.0", "id": 0, "method": method, "params": params}

    if method not in unauthenticated_methods:
        data["auth"] = auth

    data = salt.utils.json.dumps(data)

    log.info("_QUERY input:\nurl: %s\ndata: %s", str(url), str(data))

    try:
        result = salt.utils.http.query(
            url,
            method="POST",
            data=data,
            header_dict=header_dict,
            decode_type="json",
            decode=True,
            status=True,
            headers=True,
        )
        log.info("_QUERY result: %s", str(result))
        if "error" in result:
            raise SaltException(
                "Zabbix API: Status: {} ({})".format(result["status"], result["error"])
            )
        ret = result.get("dict", {})
        if "error" in ret:
            raise SaltException(
                "Zabbix API: {} ({})".format(
                    ret["error"]["message"], ret["error"]["data"]
                )
            )
        return ret
    except ValueError as err:
        raise SaltException(
            "URL or HTTP headers are probably not correct! ({})".format(err)
        )
    except OSError as err:
        raise SaltException("Check hostname in URL! ({})".format(err))


def _login(**kwargs):
    """
    Log in to the API and generate the authentication token.
    .. versionadded:: 2016.3.0
    :param _connection_user: Optional - zabbix user (can also be set in opts or pillar, see module's docstring)
    :param _connection_password: Optional - zabbix password (can also be set in opts or pillar, see module's docstring)
    :param _connection_url: Optional - url of zabbix frontend (can also be set in opts, pillar, see module's docstring)
    :return: On success connargs dictionary with auth token and frontend url, False on failure.
    """
    connargs = dict()

    def _connarg(name, key=None):
        """
        Add key to connargs, only if name exists in our kwargs or, as zabbix.<name> in __opts__ or __pillar__
        Evaluate in said order - kwargs, opts, then pillar. To avoid collision with other functions,
        kwargs-based connection arguments are prefixed with 'connection_' (i.e. '_connection_user', etc.).
        Inspired by mysql salt module.
        """
        if key is None:
            key = name

        if name in kwargs:
            connargs[key] = kwargs[name]
        else:
            prefix = "_connection_"
            if name.startswith(prefix):
                try:
                    name = name[len(prefix) :]
                except IndexError:
                    return
            val = __salt__["config.get"]("zabbix.{}".format(name), None) or __salt__[
                "config.get"
            ]("zabbix:{}".format(name), None)
            if val is not None:
                connargs[key] = val

    _connarg("_connection_user", "user")
    _connarg("_connection_password", "password")
    _connarg("_connection_url", "url")

    try:
        if connargs["user"] and connargs["password"] and connargs["url"]:
            params = {"user": connargs["user"], "password": connargs["password"]}
            method = "user.login"
            ret = _query(method, params, connargs["url"])
            auth = ret["result"]
            connargs["auth"] = auth
            connargs.pop("user", None)
            connargs.pop("password", None)
            return connargs
        else:
            raise KeyError
    except KeyError as err:
        raise SaltException("URL is probably not correct! ({})".format(err))

def _exact_match(data_list, field, value):
    match = list(filter(lambda data: value == data[field] , data_list))
    return match

def _params_extend(params, _ignore_name=False, **kwargs):
    # extend params value by optional zabbix API parameters
    for key in kwargs:
        if not key.startswith("_"):
            params.setdefault(key, kwargs[key])

    # ignore name parameter passed from Salt state module, use firstname or visible_name instead
    if _ignore_name:
        params.pop("name", None)
        if "firstname" in params:
            params["name"] = params.pop("firstname")
        elif "visible_name" in params:
            params["name"] = params.pop("visible_name")

    return params


def host_get(host=None, name=None, hostids=None, **connection_args):
    conn_args = _login(**connection_args)
    ret = False
    try:
        if conn_args:
            method = "host.get"
            params = {"output": "extend", "filter": {}}
            if not name and not hostids and not host:
                return False
            if name:
                params["filter"].setdefault("name", name)
            if hostids:
                params.setdefault("hostids", hostids)
            if host:
                params["filter"].setdefault("host", host)
            params = _params_extend(params, **connection_args)
            ret = _query(method, params, conn_args["url"], conn_args["auth"])
            return ret["result"] if len(ret["result"]) > 0 else False
        else:
            raise KeyError
    except KeyError:
        return ret

def hostgroup_get(name=None, groupids=None, hostids=None, **connection_args):
    conn_args = _login(**connection_args)
    ret = False
    try:
        if conn_args:
            method = "hostgroup.get"
            params = {"output": "extend"}
            if not groupids and not name and not hostids:
                return False
            if name:
                name_dict = {"name": name}
                params.setdefault("filter", name_dict)
            if groupids:
                params.setdefault("groupids", groupids)
            if hostids:
                params.setdefault("hostids", hostids)
            params = _params_extend(params, **connection_args)
            ret = _query(method, params, conn_args["url"], conn_args["auth"])
            return ret["result"] if len(ret["result"]) > 0 else False
        else:
            raise KeyError
    except KeyError:
        return ret

def group_ids_get(host_groups, **connection_args):
    group_ids = []
    method = "hostgroup.get"
    conn_args = _login(**connection_args)
    ret = {"result": False, "comment": ""}

    if conn_args:
       for group in host_groups:
           try:
              params   = {"output": "extend", "filter": {"name": group}}
              params   = _params_extend(params, **connection_args)
              ret_data = _query(method, params, conn_args["url"], conn_args["auth"])
              if not ret_data:
                 ret['comment'] = "Group id for group ({}) not found".format(group)
                 return ret
                 #raise SaltException("Group id for group ({}) not found".format(group))
                 #return 1, None, "Group id for group %s not found" % group
              group_ids.append(ret_data["result"][0]["groupid"])
           except KeyError:
              ret['comment'] = 'key error in zabbix group_ids_get function'
              return ret
              #return false
    else:
       raise KeyError

    #return group_ids
    ret['result'] = True
    ret['group_ids'] = group_ids
    return ret


def host_ids_get(host_names, **connection_args):
    host_ids = []
    method = "host.get"
    conn_args = _login(**connection_args)
    ret = {"result": False, "comment": ""}

    if conn_args:
       for host in host_names:
           try:
              params   = {"output": "extend", "filter": {"host": host}}
              params   = _params_extend(params, **connection_args)
              ret_data = _query(method, params, conn_args["url"], conn_args["auth"])
              if not ret_data:
                 ret['comment'] = "Host id for host ({}) not found".format(host)
                 return ret
                 #raise SaltException("Host id for host ({}) not found".format(host))
                 #return 1, None, "Host id for host %s not found" % host

              host_ids.append(ret_data["result"][0]["hostid"])
           except KeyError:
              ret['comment'] = 'key error in zabbix host_ids_get function'
              return ret
    else:
       raise KeyError

    # return host_ids
    ret['result'] = True
    ret['host_ids'] = host_ids
    return ret

def is_maintenance_active(name, wait_period=5, api_call_interval=1, **connection_args):

    ret = {"result": False, "comment": ""}
    if api_call_interval > wait_period:
        raise SaltException("Zabbix maintenance active check interval time can't be greater than wait_period")

    time_elapsed = 0
    while True:
          if time_elapsed < wait_period:
             ret_data = name_get(name, exact_match = True, **connection_args)
             if not ret_data:
                ret['comment'] = 'Failed to check maintenance %s existence'% (name)
                return ret
             maintenance_hosts    = ret_data[0]['hosts']
             match    = list(filter(lambda maintenance_host: '1' == maintenance_host['maintenance_status'] , maintenance_hosts))
             if len(match) == len(maintenance_hosts):
               ret["result"]  = True
               ret["comment"] = 'Zabbix maintenance with name %s is active'% (name)
               return ret

             time_elapsed += api_call_interval
             time.sleep(api_call_interval * 60)
          else:
             return ret

    return ret

def name_get(name, exact_match = False, **connection_args):
    conn_args = _login(**connection_args)
    ret = False
    try:
        if conn_args:
            method = "maintenance.get"
            params = {"selectGroups": "extend", "selectHosts": "extend", "selectTimeperiods": "extend", "filter": {}}

            if name:
                params["filter"].setdefault("name", name)

            params = _params_extend(params, **connection_args)
            ret = _query(method, params, conn_args["url"], conn_args["auth"])

            if len(ret["result"]) > 0 and exact_match == False:
               return ret["result"]
            elif len(ret["result"]) > 0:
               return _exact_match(ret["result"], 'name', name)
            else:
                return False
            #return ret["result"] if len(ret["result"]) > 0 and exact_match == False elif len(ret["result"]) > 0  else False
        else:
            raise KeyError
    except KeyError:
        return ret

def create(name, period, start_time, group_ids=None, host_ids=None, collect_data=0, desc="Created by Saltstack zabbix Maintenance", **connection_args):
    conn_args = _login(**connection_args)
    ret = False

    if not group_ids and not host_ids:
       raise SaltException("At least one host_ids or group_ids must be defined for each created maintenance")

    try:
       if conn_args:
          method = "maintenance.create"

          #start_time_obj = datetime.datetime.strptime(start_time, '%Y-%M-%D %H:%M')
          #start_time     = time.mktime(start_time_obj.timetuple())
          period         = 60 * int(period)  # N * 60 seconds

          if host_ids:
             if not isinstance(host_ids, list):
                host_ids  = [host_ids]
          else:
              host_ids    = []

          if group_ids:
             if not isinstance(group_ids, list):
                group_ids = [group_ids]
          else:
             group_ids    = []

          params = {"name": name,
                    "active_since": start_time,
                    "active_till": start_time + period,
                    "groupids": group_ids,
                    "hostids": host_ids,
                    "maintenance_type": collect_data,
                    "description": desc,
                    "timeperiods": [{
                        "timeperiod_type": "0",
                        "start_date": str(start_time),
                        "period": str(period)}]
          }

          params = _params_extend(params, _ignore_name=False, **connection_args)
          ret = _query(method, params, conn_args["url"], conn_args["auth"])
          return ret["result"]
       else:
          raise KeyError
    except KeyError:
        return ret

def update(name, maintenance_id, period, start_time, group_ids=None, host_ids=None, collect_data=0, desc="Created by Saltstack zabbix Maintenance", **connection_args):
    conn_args = _login(**connection_args)
    ret = False

    if not group_ids and not host_ids:
       raise SaltException("At least one host_ids or group_ids must be defined for each created maintenance")

    try:
       if conn_args:
          method = "maintenance.update"

          #start_time_obj = datetime.datetime.strptime(start_time, '%Y-%M-%D %H:%M')
          #start_time     = time.mktime(start_time_obj.timetuple())
          period         = 60 * int(period)  # N * 60 seconds

          if host_ids:
             if not isinstance(host_ids, list):
                host_ids  = [host_ids]
          else:
              host_ids    = []

          if group_ids:
             if not isinstance(group_ids, list):
                group_ids = [group_ids]
          else:
             group_ids    = []

          params = {"name": name,
                    "maintenanceid": maintenance_id,
                    "active_since": start_time,
                    "active_till": start_time + period,
                    "groupids": group_ids,
                    "hostids": host_ids,
                    "maintenance_type": collect_data,
                    "description": desc,
                    "timeperiods": [{
                        "timeperiod_type": "0",
                        "start_date": str(start_time),
                        "period": str(period)}]
          }

          params = _params_extend(params, _ignore_name=False, **connection_args)
          ret = _query(method, params, conn_args["url"], conn_args["auth"])
          return ret["result"]
       else:
            raise KeyError
    except KeyError:
        return ret


def decrease_period(name, maintenance_id, period, start_time, group_ids=None, host_ids=None, **connection_args):
    conn_args = _login(**connection_args)
    ret = False

    if not group_ids and not host_ids:
       raise SaltException("At least one host_ids or group_ids must be defined for each created maintenance")

    try:
       if conn_args:
          method = "maintenance.update"

          period         = 60 * int(period)  # N * 60 seconds

          if host_ids:
             if not isinstance(host_ids, list):
                host_ids  = [host_ids]
          else:
              host_ids    = []

          if group_ids:
             if not isinstance(group_ids, list):
                group_ids = [group_ids]
          else:
             group_ids    = []

          params = {"name": name,
                    "maintenanceid": maintenance_id,
                    "groupids": group_ids,
                    "hostids": host_ids,
                    "timeperiods": [{
                        "timeperiod_type": "0",
                        "start_date": str(start_time),
                        "period": str(period)}]
          }

          log.debug(params)

          params = _params_extend(params, _ignore_name=True, **connection_args)

          log.debug(params)
          log.debug("PANKAJ")
          ret = _query(method, params, conn_args["url"], conn_args["auth"])
          return ret["result"]
       else:
            raise KeyError
    except KeyError:
        return ret

def delete(maintenance_ids, **connection_args):
    conn_args = _login(**connection_args)
    ret = False
    try:
        if conn_args:
            method = "maintenance.delete"
            if not isinstance(maintenance_ids, list):
               maintenance_ids = [maintenance_ids]

            params = { maintenance_ids }
            ret = _query(method, params, conn_args["url"], conn_args["auth"])
            return ret["result"]
        else:
            raise KeyError
    except KeyError:
        return ret
