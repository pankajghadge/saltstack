from __future__ import absolute_import, print_function, unicode_literals

import logging
import xml.etree.ElementTree as ET
#from lxml import etree as ET

log = logging.getLogger(__name__)

# Define the module's virtual name
__virtualname__ = 'salt_xml'


def __virtual__():
    '''
    Only load the module if all modules are imported correctly.
    '''
    return __virtualname__

def get_value(file, element, namespaces=None):
    '''
        get_value /tmp/test.xml ".//element"
    '''
    try:
        root = ET.parse(file)
        element = root.find(element, namespaces)
        return element.text
    except AttributeError:
        log.error("Unable to find element matching %s", element)
        return False

def set_value(file, element, value, namespaces=None, prefix_namespaces=False):
    '''
        salt '*' salt_xml.set_value /tmp/test.xml ".//element" "new value"
    '''
    try:
        root = ET.parse(file)
        relement = root.find(element, namespaces)
    except AttributeError:
        log.error("Unable to find element matching %s", element)
        return False

    if namespaces:
       if prefix_namespaces:
          for prefix, uri in namespaces.items():
              ET.register_namespace(prefix, uri)
       else:
          for prefix, uri in namespaces.items():
              ET.register_namespace('', uri)

    relement.text = str(value)
    root.write(file)
    return True

def append_value(file, element, value, namespaces=None, prefix_namespaces=False):
    '''
        salt '*' salt_xml.set_value /tmp/test.xml ".//element" "new value"
    '''

    cur_value = get_value(file, element, namespaces)
    if cur_value and value not in cur_value:
       value = cur_value + value
    elif value in cur_value:
       log.error("Text already exists in XML tag")
       return True
    else:
       return False

    try:
        root = ET.parse(file)
        relement = root.find(element, namespaces)
    except AttributeError:
        log.error("Unable to find element matching %s", element)
        return False

    if namespaces:
       if prefix_namespaces:
          for prefix, uri in namespaces.items():
              ET.register_namespace(prefix, uri)
       else:
          for prefix, uri in namespaces.items():
              ET.register_namespace('', uri)

    relement.text = str(value)
    root.write(file)
    return True


def get_attribute(file, element, namespaces=None):
    '''
        salt '*' salt_xml.get_attribute /tmp/test.xml ".//element[@id='3']"
    '''
    try:
        root = ET.parse(file)
        element = root.find(element, namespaces)
        return element.attrib
    except AttributeError:
        log.error("Unable to find element matching %s", element)
        return False


def set_attribute(file, element, key, value, namespaces=None, prefix_namespaces=False):
    '''
        salt '*' salt_xml.set_attribute /tmp/test.xml ".//element[@id='3']" editedby "gal"
    '''
    try:
        root = ET.parse(file)
        element = root.find(element,namespaces)
    except AttributeError:
        log.error("Unable to find element matching %s", element)
        return False

    if namespaces:
       if prefix_namespaces:
          for prefix, uri in namespaces.items():
              ET.register_namespace(prefix, uri)
       else:
          for prefix, uri in namespaces.items():
              ET.register_namespace('', uri)

    element.set(key, str(value))
    root.write(file)
    return True

def count_nodes(file, element, namespaces=None):
   try:
        root = ET.parse(file)
        element = root.findall(element,namespaces)
        return len(element)
   except AttributeError:
        log.error("Unable to find element matching %s", element)
        return False

'''
if __name__ == "__main__":
    logging.info("Begin")
    ns = {'java': 'http://java.sun.com/xml/ns/javaee', 'w3': 'http://www.w3.org/2001/XMLSchema-instance'}
    print(append_value('/opt/web.xml', "./java:filter/java:init-param[java:param-name='skipFilterUrlPatterns']/java:param-value", ",/resources/SOW4P/synchro,/resources/SOW4P/ticket,",ns))
'''
