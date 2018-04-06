#Repo for mariaDB
{% from "base/mariadb/latest/map.jinja" import os_rel_map with context %}
	
{%- set stable_version = '10.2' %}
{%- set repo_version = salt['pillar.get']('mariadb:repo_version', stable_version) %}
{%- set repourl = salt['pillar.get']('mariadb:repourl', 'http://yum.mariadb.org') %}

# Install MariaDB repository
mariadb_repo:
  pkgrepo.managed:
    - humanname: MariaDB {{ repo_version }}
    - baseurl:  {{ repourl }}/{{ repo_version }}/{{ os_rel_map.baseurlend }}
    - gpgcheck: 1
    - gpgkey: https://yum.mariadb.org/RPM-GPG-KEY-MariaDB