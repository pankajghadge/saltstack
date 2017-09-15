include:
  - tools.s3cmd

{% for s3_backup in salt['pillar.get']('s3cmd:backup', []) %}

{%- if not s3_backup['source'] is defined %}
custom_raise:
  test.fail_without_changes:
    - name: "AWS S3 Source value is not defined in pillar!!!"
    - failhard: True
{%- endif %}

{%- if not s3_backup['destination'] is defined %}
custom_raise:
  test.fail_without_changes:
    - name: "AWS S3 Destination value is not defined in pillar!!!"
    - failhard: True
{%- endif %}

{%- if not (( s3_backup['cron_hour'] is defined ) or ( s3_backup['cron_minute'] is defined )) %}
custom_raise:
  test.fail_without_changes:
    - name: "Cron Hour and Minute values are not set in pillar!!!"
    - failhard: True
{%- endif %}


{%- if s3_backup['delete'] is defined and s3_backup['delete'] == True %}
{% set s3_cron_script = 's3cmd sync --delete-removed ' ~ s3_backup['source'] ~ ' ' ~ s3_backup['destination'] %}
{%- else %}
{% set s3_cron_script = 's3cmd sync --no-delete-removed ' ~ s3_backup['source'] ~ ' ' ~ s3_backup['destination'] %}
{%- endif %}

{% set s3_backup_id = 's3_backup_' ~ loop.index %}
{{ s3_backup_id }}:
  {%- if s3_backup['cron_present'] is defined and s3_backup['cron_present'] == False %}
  cron.absent:
  {%- else %}
  cron.present:
  {%- endif %}
    - name: {{ s3_cron_script }}
    {%- if s3_backup['cron_identifier'] is defined %}
    - identifier: {{ s3_backup['cron_identifier'] }}
    {%- endif %}
    - user: {{ s3_backup['cron_user'] |default('root') }}
    - minute: {{ s3_backup['cron_minute'] }}
    - hour: {{ s3_backup['cron_hour'] }}

{% endfor %}
