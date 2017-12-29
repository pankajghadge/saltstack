include:
  - java

{% from "tomcat/map.jinja" import os_rel_map with context %}

{% set tomcat_version = salt['pillar.get']('tomcat:version', '7.0.54') %}
{% set tomcat_base_version = salt['pillar.get']('tomcat:base_version', '7') %}
{% set install_path = salt['pillar.get']('tomcat:install_path', '/usr/local/tomcat') %}

# Download Tomcat and manage the service
tomcat:
  file.managed:
    - name: {{ install_path }}/apache-tomcat-{{tomcat_version}}.tar.gz
    - source: http://archive.apache.org/dist/tomcat/tomcat-{{ tomcat_base_version }}/v{{ tomcat_version }}/bin/apache-tomcat-{{ tomcat_version }}.tar.gz
    - source_hash: http://archive.apache.org/dist/tomcat/tomcat-{{ tomcat_base_version }}/v{{ tomcat_version }}/bin/apache-tomcat-{{ tomcat_version }}.tar.gz.md5
    - makedirs: True
  service:
    - enable: True
    - running
    - require:
      - file: {{ os_rel_map.service_watch_file }}
    - watch:
      - file: {{ install_path }}/apache-tomcat-{{tomcat_version}}/conf/tomcat-users.xml
      - file: {{ os_rel_map.service_watch_file }}



# Extract the Tomcat archive
untar_tomcat:
  cmd.run:
    - name: 'tar xf {{ install_path }}/apache-tomcat-{{tomcat_version}}.tar.gz'
    - unless: 'test -d {{ install_path }}/apache-tomcat-{{tomcat_version}}'
    - cwd: {{ install_path }}
    - require:
      - file: tomcat


# Making a symlink
{{ install_path }}/latest:
  file.symlink:
    - target: {{ install_path }}/apache-tomcat-{{tomcat_version}}
    - makedirs: True



{{ os_rel_map.service_watch_file }}:
  file.managed:
    - source: {{ os_rel_map.init_file_src }}
    - mode: 0755
    - template: jinja
    - context:
        install_path: {{ install_path }}

      
# Allow Salt to use the App-Manager
{{ install_path }}/apache-tomcat-{{tomcat_version}}/conf/tomcat-users.xml:
  file.managed:
    - source: salt://base/tomcat/files/tomcat-users.xml.j2
    - template: jinja
    - require: 
      - cmd: untar_tomcat


#{{ install_path }}/apache-tomcat-{{tomcat_version}}/webapps/manager/WEB-INF/web.xml:
#  file.managed:
#    - source: salt://base/tomcat/files/web.xml
#    - template: jinja
#    - context:
#        tomcat_base_version: {{ tomcat_base_version }}
#    - require:
#      - cmd: untar_tomcat


# Wait for App-Manager fully available
wait-for-tomcatmanager:
  tomcat:
    - wait
    - timeout: 300
    - require:
      - service: tomcat


# Remove defaults webapps
{% for dir in ['docs', 'examples', 'host-manager'] %}
{{ install_path }}/apache-tomcat-{{tomcat_version}}/webapps/{{ dir }}:
  file.absent:
    - require:
      - cmd: untar_tomcat
{% endfor %}


# Making a symlink to /var/log for Tomcat logs
/var/log/tomcat:
  file.symlink:
    - target: {{ install_path }}/latest/logs


# Configuring logrotate on Tomcat logs
logrotate:
  file.managed:
    - name: /etc/logrotate.d/tomcat
    - source: salt://base/tomcat/files/logrotate
    - template: jinja
    - context:
        install_path: {{ install_path }}

vm.swappiness:
  sysctl.present:
    - value: 1

tomcat-restart:
  module:
    - wait
    - name: service.restart
    - m_name: tomcat

