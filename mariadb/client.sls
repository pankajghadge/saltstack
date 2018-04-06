#MariaDB Client
{% from "base/mariadb/latest/map.jinja" import os_rel_map with context %}
include:
  - .repo

mariadb-client:
  pkg.installed:
    - name: {{ os_rel_map.mariadb_client }}

