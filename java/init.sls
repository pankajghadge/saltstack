{% set version_long  = salt['pillar.get']('java:version:long', '1.7.0_60') %}
{% set version_short = salt['pillar.get']('java:version:short', '7u60') %}


jre:
  file.managed:
    - name: /usr/local/java/jre-{{ version_short}}-linux-x64.tar.gz
    - source: http://salt/files/java/jre-{{ version_short}}-linux-x64.tar.gz
    - source_hash: http://salt/files/java/jre-{{ version_short}}-linux-x64.tar.gz.md5
    - makedirs: True


untar_jre:
  cmd.run:
    - name: 'tar xf /usr/local/java/jre-{{ version_short}}-linux-x64.tar.gz'
    - unless: 'test -d /usr/local/java/jre{{version_long}}'
    - cwd: /usr/local/java
    - require:
      - file: jre

/usr/local/java/latest:
  file.symlink:
    - target: /usr/local/java/jre{{ version_long }}
    - makedirs: True


/etc/profile:
  file.append:
    - text: |
        export JAVA_HOME=/usr/local/java/latest
        export PATH=$PATH:/usr/local/java/latest/bin

/etc/sysconfig/java:
  file.managed:
    - contents: JAVA_HOME=/usr/local/java/latest

jre_java_home_env:
  environ.setenv:
    - name: JAVA_HOME
    - value: /usr/local/java/latest
    - update_minion: True
