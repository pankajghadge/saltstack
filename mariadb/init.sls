{% set current_path = sls.split('.') | join('/') %}

{% from "base/mariadb/latest/files/defaults.yaml" import rawmap with context %}
{%- set mysql_conf = salt['grains.filter_by'](rawmap, grain='os', merge=salt['pillar.get']('mariadb:server:lookup')) %}
{% set os_family = salt['grains.get']('os_family', None) %}

#MariaDB
{% set mysql_datadir = salt['pillar.get']('mariadb:server:datadir', '/data') %}
{% from "base/mariadb/latest/map.jinja" import os_rel_map with context %}

include:
  - .repo

mariadb:
  pkg.installed:
    - pkgs:
      - {{ os_rel_map. mariadb_server }}
  service:
    - name: {{ os_rel_map.mariadb_service }}
    - running
    - enable: True
    - require:
      - pkg: mariadb
      - cmd: {{ mysql_datadir }}/mysql
      - file: /var/log/mysql
      - file: /var/lib/mysql
      - sysctl: fs.file-max
      - pkgrepo: mariadb_repo
    - watch:
      - file: /etc/my.cnf.d/server.cnf

{{ os_rel_map.limit_conf_file_name }}:
  file.managed:
    - source: {{ os_rel_map.limit_conf_file }}
    - template: jinja
    - makedirs: True
    - require:
      - pkg: mariadb

{{ mysql_datadir }}/mysql:
  cmd.run:
    - name: mv /var/lib/mysql {{ mysql_datadir }}
    - unless: test -d {{ mysql_datadir }}/mysql

/var/log/mysql:
  file.directory:
    - makedirs: True
    - user: mysql
    - group: mysql

fs.file-max:
  sysctl.present:
    - value: 66559

/var/lib/mysql:
  file.directory:
    - makedirs: True
    - user: mysql
    - group: mysql

mysql_server_config:
  file.managed:
    - name: {{ mysql_conf.config_directory + mysql_conf.server_config.file }}
    - template: jinja
    - source: salt://{{ current_path }}/files/server.cnf.jinja
    {% if os_family in ['Debian', 'Gentoo', 'RedHat'] %}
    - user: root
    - group: root
    - mode: 644
    {% endif %}


# The following states can be used by other states to trigger a restart or reload as needed.
mariadb-reload:
  module:
    - wait
    - name: service.reload
    - m_name: {{ os_rel_map.mariadb_service }}

mariadb-restart:
  module:
    - wait
    - name: service.restart
    - m_name: {{ os_rel_map.mariadb_service }}
