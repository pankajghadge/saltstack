import logging

log = logging.getLogger(__name__)

def __virtual__():
    """
    Only load if the XML execution module is available.
    """
    if "salt_xml.get_value" in __salt__:
        return "salt_xml"
    else:
        return False, "The salt_xml execution module is not available"


def set_value(name, xpath, value, namespaces=None, prefix_namespaces=False, **kwargs):
    """
        ensure_value_true:
          salt_xml.set_value:
            - name: /tmp/web.xml
            - xpath: ./java:filter/java:init-param[java:param-name='skipFilterUrlPatterns']/java:param-value
            - value: ",/resources/SOW4P/synchro,/resources/SOW4P/ticket,"
    """
    ret = {"name": name, "changes": {}, "result": True, "comment": ""}

    if "test" not in kwargs:
        kwargs["test"] = __opts__.get("test", False)

    current_value = __salt__["salt_xml.get_value"](name, xpath, namespaces)
    if not current_value:
        ret["result"] = False
        ret["comment"] = "xpath query {} not found in {}".format(xpath, name)
        return ret

    if current_value != value:
        if kwargs["test"]:
            ret["result"] = None
            ret["comment"] = "{} will be updated".format(name)
            ret["changes"] = {name: {"old": current_value, "new": value}}
        else:
            results = __salt__["salt_xml.set_value"](name, xpath, value, namespaces, prefix_namespaces)
            ret["result"] = results
            ret["comment"] = "{} updated".format(name)
            ret["changes"] = {name: {"old": current_value, "new": value}}
    else:
        ret["comment"] = "{} is already present".format(value)

    return ret

def append_value(name, xpath, value, namespaces=None, prefix_namespaces=False, **kwargs):
    """
        ensure_value_true:
          salt_xml.append_value:
            - name: /tmp/web.xml
            - xpath: ./java:filter/java:init-param[java:param-name='skipFilterUrlPatterns']/java:param-value
            - value: ",/resources/SOW4P/synchro,/resources/SOW4P/ticket,"
    """
    ret = {"name": name, "changes": {}, "result": True, "comment": ""}

    if "test" not in kwargs:
        kwargs["test"] = __opts__.get("test", False)

    current_value = __salt__["salt_xml.get_value"](name, xpath, namespaces)
    if not current_value:
        ret["result"] = False
        ret["comment"] = "xpath query {} not found in {}".format(xpath, name)
        return ret

    if value not in current_value:
        if kwargs["test"]:
            ret["result"] = None
            ret["comment"] = "{} will be updated".format(name)
            ret["changes"] = {name: {"old": current_value, "new": current_value+value}}
        else:
            results = __salt__["salt_xml.append_value"](name, xpath, value, namespaces, prefix_namespaces)
            ret["result"] = results
            ret["comment"] = "{} updated".format(name)
            ret["changes"] = {name: {"old": current_value, "new": current_value+value }}
    else:
        ret["comment"] = "{} is already present".format(value)

    return ret

def set_attribute(name, xpath, value, namespaces=None, prefix_namespaces=False, **kwargs):
    """
        ensure_value_true:
          salt_xml.append_value:
            - name: /tmp/web.xml
            - xpath: ./java:filter/java:init-param[java:param-name='skipFilterUrlPatterns']/java:param-value
            - value: ",/resources/SOW4P/synchro,/resources/SOW4P/ticket,"
    """
    ret = {"name": name, "changes": {}, "result": True, "comment": ""}

    if "test" not in kwargs:
        kwargs["test"] = __opts__.get("test", False)

    current_value = __salt__["salt_xml.get_attribute"](name, xpath, namespaces)
    if not current_value:
        ret["result"] = False
        ret["comment"] = "xpath query {} not found in {}".format(xpath, name)
        return ret

    if value not in current_value:
        if kwargs["test"]:
            ret["result"] = None
            ret["comment"] = "{} will be updated".format(name)
            ret["changes"] = {name: {"old": current_value, "new": value}}
        else:
            results = __salt__["salt_xml.set_attribute"](name, xpath, value, namespaces, prefix_namespaces)
            ret["result"] = results
            ret["comment"] = "{} updated".format(name)
            ret["changes"] = {name: {"old": current_value, "new": value}}
    else:
        ret["comment"] = "XML attribute {} is already present".format(value)

    return ret
