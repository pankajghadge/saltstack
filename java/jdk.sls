{% set version_long  = salt['pillar.get']('java:version:long', '1.7.0_60') %}
{% set version_short = salt['pillar.get']('java:version:short', '7u60') %}


jdk:
  file.managed:
    - name: /usr/local/java/jdk-{{ version_short}}-linux-x64.tar.gz
    - source: http://salt/files/java/jdk-{{ version_short}}-linux-x64.tar.gz
    - source_hash: http://salt/files/java/jdk-{{ version_short}}-linux-x64.tar.gz.md5
    - makedirs: True


jdk_untar:
  cmd.run:
    - name: 'tar xf /usr/local/java/jdk-{{ version_short}}-linux-x64.tar.gz'
    - unless: 'test -d /usr/local/java/jdk{{version_long}}'
    - cwd: /usr/local/java
    - require:
      - file: jdk

jdk_symlink:
  file.symlink:
    - name: /usr/local/java/latest
    - target: /usr/local/java/jdk{{ version_long }}
    - makedirs: True


jdk_profile_add:
  file.append:
    - name: /etc/profile
    - text: |
        export JAVA_HOME=/usr/local/java/latest
        export PATH=$PATH:/usr/local/java/latest/bin

jdk_sysconfig_add:
  file.managed:
    - name: /etc/sysconfig/java
    - contents: JAVA_HOME=/usr/local/java/latest

jdk_java_home_env:
  environ.setenv:
    - name: JAVA_HOME
    - value: /usr/local/java/latest
    - update_minion: True
