{% set current_path = sls.split('.')[:-1] | join('/') %}

{% set mysql_root_password = salt['pillar.get']('mariadb:server:root_password', 'root') %}
/etc/logrotate.d/mysql:
  file.managed:
    - source: salt://{{ current_path }}/files/logrotate
    - template: jinja
    - mode: 400
    - template: jinja
    - makedirs: True
    - context:
        mysql_root_password: {{ mysql_root_password }}
