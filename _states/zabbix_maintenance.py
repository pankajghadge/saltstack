# -*- coding: utf-8 -*-
"""
    :maturity:      develop
    :platform:      Zabbix maintenance
    :Developer:     Pankaj Ghadge 
"""

# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals

# Import Salt libs
import salt.utils.json

# Import 3rd-party libs
from salt.ext import six
import dateutil.parser
import time
import datetime

import logging
log = logging.getLogger(__name__)


# set up virtual function
def __virtual__():
    if "zabbix_maintenance.host_get" in __salt__:
        return "zabbix_maintenance"
    return (False, "Zabbix maintenance module could not be loaded")

def create(name, period, start_time, host_groups=None, host_names=None, collect_data=0, maintenance_window=None, desc="Created by Saltstack zabbix Maintenance", **connection_args):

    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    group_ids = []
    host_ids  = []

    try:
       start_time = time.mktime(dateutil.parser.parse(start_time).timetuple())
    except (ValueError,IOError) as err:
       ret['comment'] = err
       return ret

    if not host_groups and not host_names:
       ret['comment'] = 'At least one host_groups or host_names must be defined for each created maintenance'
       return ret

    # is this host group currently configured in zabbix?
    if host_groups:
       if not isinstance(host_groups, list):
          host_groups         = [host_groups]
       host_groups_ret     = __salt__["zabbix_maintenance.group_ids_get"](host_groups, **connection_args)
       if host_groups_ret['result']:
          group_ids = host_groups_ret['group_ids']
       if len(group_ids) == 0:
          ret['comment'] = 'Host Groups does not exists on Zabbix server'
          return ret

    # is this host name currently configured in zabbix?
    if host_names:
       if not isinstance(host_names, list):
          host_names        = [host_names]
       host_names_ret    = __salt__["zabbix_maintenance.host_ids_get"](host_names, **connection_args)
       if host_names_ret['result']:
          host_ids = host_names_ret['host_ids']
       if len(host_ids) == 0:
          ret['comment'] = 'Host names does not exists on Zabbix server'
          return ret

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'Will create a maintenance on Zabbix server'
       return ret

    # is this maintenance currently configured?
    search = __salt__["zabbix_maintenance.name_get"](name, exact_match = True, **connection_args)
    if not search:
       result = __salt__["zabbix_maintenance.create"](name, period, start_time, group_ids, host_ids, collect_data, desc, **connection_args)
       ret["comment"] = "Zabbix maintenance was successfully created."

       result_is_active = __salt__["zabbix_maintenance.is_maintenance_active"](name, **connection_args)

       if result_is_active['result']:
          ret["comment"] = "Zabbix maintenance was successfully created and hosts maintenance status is active"
       ret["result"] = True
       ret["changes"]["old"] = {}
       ret["changes"]["new"] = "Zabbix maintenance has been created with id " + str(result['maintenanceids'])
    else:
        ret["result"] = True
        ret["comment"] = "This Zabbix maintenance already exists in zabbix . No action taken"

    return ret

def update(name, period, start_time, host_groups=None, host_names=None, collect_data=0, maintenance_window=None, desc="Created by Saltstack zabbix Maintenance", **connection_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    group_ids = []
    host_ids  = []

    try:
       start_time = time.mktime(dateutil.parser.parse(start_time).timetuple())
    except (ValueError,IOError) as err:
       ret['comment'] = err
       return ret

    if not host_groups and not host_names:
       ret['comment'] = 'At least one host_groups or host_names must be defined for each created maintenance'
       return ret

    # is this host group currently configured in zabbix?
    if host_groups:
       if not isinstance(host_groups, list):
          host_groups         = [host_groups]
       host_groups_ret     = __salt__["zabbix_maintenance.group_ids_get"](host_groups, **connection_args)
       if host_groups_ret['result']:
          group_ids = host_groups_ret['group_ids']
       if len(group_ids) == 0:
          ret['comment'] = 'Host Groups does not exists on Zabbix server'
          return ret

    # is this host name currently configured in zabbix?
    if host_names:
       if not isinstance(host_names, list):
          host_names        = [host_names]
       host_names_ret    = __salt__["zabbix_maintenance.host_ids_get"](host_names, **connection_args)
       if host_names_ret['result']:
          host_ids = host_names_ret['host_ids']
       if len(host_ids) == 0:
          ret['comment'] = 'Host names does not exists on Zabbix server'
          return ret

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'Will update a maintenance on Zabbix server'
       return ret

    # is this maintenance currently configured?
    search = __salt__["zabbix_maintenance.name_get"](name, exact_match = True, **connection_args)
    if len(search) == 1:
       maintenanceid = search[0]['maintenanceid']
       result = __salt__["zabbix_maintenance.update"](name, maintenanceid, period, start_time, group_ids, host_ids, collect_data, desc, **connection_args)
       ret["result"] = True
       ret["changes"]["old"] = {}
       ret["changes"]["new"] = "Zabbix maintenance with id ({}) has been updated".format(maintenanceid)
       ret["comment"] = "Zabbix maintenance was successfully updated"
    else:
        ret["result"] = False
        ret["comment"] = "This Zabbix maintenance does not exists in zabbix . No update action taken"

    return ret


def decrease_period(name, period=5, host_groups=None, host_names=None, **connection_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    group_ids = []
    host_ids  = []

    now          = datetime.datetime.now().replace(second=0)
    current_time = time.mktime(now.timetuple())

    if not host_groups and not host_names:
       ret['comment'] = 'At least one host_groups or host_names must be defined for each created maintenance'
       return ret

    # is this host group currently configured in zabbix?
    if host_groups:
       if not isinstance(host_groups, list):
          host_groups         = [host_groups]
       host_groups_ret     = __salt__["zabbix_maintenance.group_ids_get"](host_groups, **connection_args)
       if host_groups_ret['result']:
          group_ids = host_groups_ret['group_ids']
       if len(group_ids) == 0:
          ret['comment'] = 'Host Groups does not exists on Zabbix server'
          return ret

    # is this host name currently configured in zabbix?
    if host_names:
       if not isinstance(host_names, list):
          host_names        = [host_names]
       host_names_ret    = __salt__["zabbix_maintenance.host_ids_get"](host_names, **connection_args)
       if host_names_ret['result']:
          host_ids = host_names_ret['host_ids']
       if len(host_ids) == 0:
          ret['comment'] = 'Host names does not exists on Zabbix server'
          return ret

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'Will decrease the maintenance period on Zabbix server'
       return ret

    # is this maintenance currently configured?
    search = __salt__["zabbix_maintenance.name_get"](name, exact_match = True, **connection_args)
    if len(search) == 1:
       maintenanceid = search[0]['maintenanceid']
       start_time    = search[0]['active_since']
       period        = int((current_time - float(start_time))/60 + period)
       start_time    = int(search[0]['active_since'])

       result = __salt__["zabbix_maintenance.decrease_period"](name, maintenanceid, period, start_time, group_ids, host_ids, **connection_args)
       ret["result"] = True
       ret["changes"]["old"] = {}
       ret["changes"]["new"] = "Zabbix maintenance period with id ({}) has been updated".format(maintenanceid)
       ret["comment"] = "Zabbix maintenance period was successfully updated"
    else:
        ret["result"] = False
        ret["comment"] = "This Zabbix maintenance does not exists in zabbix . No update action taken"

    return ret

def delete(name, **connection_args):
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'Will delete a maintenance on Zabbix server'
       return ret

    search = __salt__["zabbix_maintenance.name_get"](name, exact_match = True, **connection_args)

    if search:
       maintenanceids = [search['maintenanceid']]
       result = __salt__["zabbix_maintenance.delete"](maintenanceids, **connection_args)
       ret["result"] = True
       ret["changes"]["old"] = {}
       ret["changes"]["new"] = "Zabbix maintenance with id ({}) has been updated".format(maintenanceid)
       ret["comment"] = "Zabbix maintenance was successfully updated"
    else:
        ret["result"] = True
        ret["comment"] = "This Zabbix maintenance does not exists in zabbix . No update action taken"

    return ret

