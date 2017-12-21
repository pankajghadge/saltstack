s3cmd:
  pkg.installed

s3cmd-configuration:
  file.managed:
    - name: {{ salt['pillar.get']('s3cmd:conf:home_path', '/root') }}/.s3cfg
    - source: salt://tools/s3cmd/files/s3cfg.conf
    - template: jinja
    - mode: 0600
    - require:
      - pkg: s3cmd
