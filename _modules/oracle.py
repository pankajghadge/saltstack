# -*- coding: utf-8 -*-
'''
Written by: pankaj ghadge
Oracle Module
'''

from __future__ import absolute_import, print_function, unicode_literals
import logging
import sys
import os
from salt.ext import six
from salt.utils.decorators import depends
import time
import re
import subprocess

log = logging.getLogger(__name__)
connargs = dict()

try:
    import cx_Oracle
    import gevent
    from gevent import Greenlet
    import gevent.subprocess
    HAS_CX_ORACLE = True
    authorization_modes = {"SYSASM": cx_Oracle.SYSASM, "SYSBKP": cx_Oracle.SYSBKP, "SYSDBA": cx_Oracle.SYSDBA, "SYSDGD": cx_Oracle.SYSDGD, "SYSKMT": cx_Oracle.SYSKMT, "SYSOPER": cx_Oracle.SYSOPER, "SYSRAC": cx_Oracle.SYSRAC, "PRELIM_AUTH": cx_Oracle.PRELIM_AUTH}
    rman_authorization_modes = {"SYSBKP": 'sysbackup', "SYSDBA": 'sysdba'}
    rman_action = {"restore": "auxiliary", "backup": "target"}
except ImportError:
    HAS_CX_ORACLE = False

__virtualname__ = 'devops_oracle'

def __virtual__():
    '''
    Load module only if cx_Oracle installed
    '''
    if HAS_CX_ORACLE:
        return __virtualname__
    return (False, 'The oracle execution and other supported modules not loaded: python oracle or gevent library not found.')

def _cx_oracle_req():
    '''
    Fallback function stub
    '''
    return 'Need "cx_Oracle" and Oracle Client installed for this function exist'


def _is_oracle_home_set():

    oracle_home = os.environ.get('ORACLE_HOME')

    if not oracle_home:
       log.debug('Oracle home is not set. Please set the ORACLE_HOME before executing this module')
       return False
    return True

def _connect(**kwargs):

    """ Connect to the oracle database. """

    #connargs = dict()
    global connargs

    def _connarg(name, key=None, get_opts=True):
        '''
        Oracle connection configuration can be set in /etc/salt/minion
        configs might look like:
        oracle.host: "localhost"
        oracle.user: "sys"
        oracle.pass: ""
        oracle.port: 1521

        Oracle connection configuration can also be set in pillar
        oracle:
          host: "localhost"
          user: "sys"
          pass: ""
          port: 1521

        Add key to connargs, only if name exists in our kwargs or,
        if get_opts is true, as oracle.<name> in __opts__ or __pillar__
        If get_opts is true, evaluate in said order - kwargs, opts
        then pillar. To avoid collision with other functions,
        kwargs-based connection arguments are prefixed with 'connection_'
        (i.e. 'connection_host', 'connection_user', etc.).
        '''
        if key is None:
           key = name

        if name in kwargs:
           connargs[key] = kwargs[name]
        elif get_opts:
           prefix = 'connection_'
           if name.startswith(prefix):
              try:
                  name = name[len(prefix):]
              except IndexError:
                  return
           val = __salt__['config.option']('oracle.{0}'.format(name), None) or \
                 __salt__['config.get']('oracle.{0}'.format(name), None) or \
                 __salt__['config.get']('oracle:{0}'.format(name), None) or \
                 __salt__['pillar.get']('oracle.{0}'.format(name), None)
           if val is not None:
              connargs[key] = val

    get_opts = True
    _connarg('connection_host', 'host', get_opts)
    _connarg('connection_user', 'user', get_opts)
    _connarg('connection_pass', 'pass', get_opts)
    _connarg('connection_port', 'port', get_opts)
    _connarg('connection_sid', 'sid', get_opts)
    _connarg('connection_mode', 'mode', get_opts)

    #connargs['dsn'] = cx_Oracle.makedsn(host=connargs['host'], port=connargs['port'], sid=connargs['sid']).replace('SID','SERVICE_NAME')
    connargs['dsn'] = '{0}:{1}/{2}'.format(connargs['host'], connargs['port'], connargs['sid'])
    try:
        if connargs['mode'] is not None:
           #conn = cx_Oracle.connect(user=connargs['user'], password=connargs['pass'], dsn=connargs['dsn'], mode=connargs['mode'])
           conn = cx_Oracle.connect(connargs['user'], connargs['pass'], connargs['dsn'], mode=connargs['mode'])
        else:
           #conn = cx_Oracle.connect(user=connargs['user'], password=connargs['pass'], dsn=connargs['dsn'])
           conn = cx_Oracle.connect(connargs['user'], connargs['pass'], connargs['dsn'])
    except cx_Oracle.DatabaseError as exc:
        err = 'Oracle Error {0}'.format(exc)
        __context__['devops_oracle.error'] = err
        log.error(err)
        return None

    return conn

def _disconnect(conn):
    """
    Disconnect from the database. If this fails, for instance
    if the connection instance doesn't exist, ignore the exception.
    """

    try:
        conn.cursor.close()
        conn.db.close()
    except cx_Oracle.DatabaseError:
        pass

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def unmount(sid, connection_mode='SYSDBA', **connection_args):

    '''
    sid
        The name of the database to unmount
    **connection_args
        Oracle Connection arguments
    '''

    ret = {'result': False}
    global authorization_modes
    mode = authorization_modes[connection_mode]

    connection_args.update({'connection_sid': sid, 'connection_mode': mode})
    conn = _connect(**connection_args)
    if conn is None:
       return ret

    try:
       conn.startup(force=True)
       log.info('Database dismounted successfully')
       ret['result'] = True
    except cx.DatabaseError as err:
       ret['comment'] = str(err)

    return ret

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def shutdown_immediate(sid, connection_mode='SYSDBA', **connection_args):

    '''
    Shutting down a database
    sid
        The name of the database to shutdown the database
    **connection_args
        Oracle Connection arguments

    It is only possible in Oracle 10g Release 2 and higher.
    This salt script requires cx_Oracle 4.3 and higher.
    Make sure environment variable sid is part of **connection_args
    https://github.com/oracle/python-cx_Oracle/blob/master/samples/DatabaseShutdown.py
    '''

    ret = {'result': False}

    global authorization_modes
    mode = authorization_modes[connection_mode]

    connection_args.update({'connection_sid': sid, 'connection_mode': mode})
    conn = _connect(**connection_args)
    if conn is None:
       return ret

    try:
        conn.shutdown(mode=cx_Oracle.DBSHUTDOWN_IMMEDIATE)
    except cx_Oracle.DatabaseError as err:
        ret['comment'] = 'cannot shutdown: {}'.format(err)
        return ret

    sqls = [
        'alter database close normal',
        'alter database dismount',
    ]

    with conn.cursor() as cur:
         for sql in sqls:
             try:
                 cur.execute(sql)
             except cx_Oracle.DatabaseError as err:
                 ret['comment'] = '{}: {}'.format(sql, err)
                 return ret

         try:
             conn.shutdown(mode=cx_Oracle.DBSHUTDOWN_FINAL)
             ret['result'] = True
             log.info('Database shut down successfully')
         except cx_Oracle.DatabaseError as err:
             ret['comment'] = 'shutdown final: {}'.format(err)

    return ret

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def shutdown_abort(sid, connection_mode='SYSDBA', **connection_args):

    '''
    Shutting down abort a database
    sid
        The name of the database to shutdown the database
    **connection_args
        Oracle Connection arguments
    '''

    ret = {'result': False}
    global authorization_modes
    mode = authorization_modes[connection_mode]

    connection_args.update({'connection_sid': sid, 'connection_mode': mode})
    conn = _connect(**connection_args)
    if conn is None:
       return ret

    try:
       conn.startup(force=True)
       conn.shutdown(mode = cx_Oracle.DBSHUTDOWN_ABORT)
       log.info('Database shutsown abort successfully')
       ret['result'] = True
    except cx.DatabaseError as err:
       ret['comment'] = str(err)

    return ret

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def startup(sid, force=False, restrict=False, pfile=None, connection_mode='SYSDBA', **connection_args):

    '''
    Start a database. It will not mount and open a database
    Please run these query using run_query module:
        "alter database mount"
        "alter database open"
    sid
        The name of the database to shutdown the database
    force
        if True then force start a database
    restrict
        if True then start a database in restricted mode
    **connection_args
        Oracle Connection arguments
    '''

    ret = {'result': False}
    global authorization_modes
    mode = authorization_modes[connection_mode]

    connection_args.update({'connection_sid': sid, 'connection_mode': mode | cx_Oracle.PRELIM_AUTH})
    conn = _connect(**connection_args)

    if conn is None:
       return ret

    if restrict:
       log.info('Starting up a database {} in restricted mode'.format(sid))
    else:
       log.info('Starting up a database {} in unrestricted mode'.format(sid))

    if force:
       log.info('Forcing a database {} to Start'.format(sid))

    try:
        conn.startup(force=force, restrict=restrict)
        log.info('database started successfully. Run alter database mount and open command')
    except cx_Oracle.DatabaseError as err:
        ret['comment'] = 'cannot startup: {}'.format(err)
        return ret

    ret['result'] = True
    return ret

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def run_query(sid, query, connection_mode=None, **connection_args):

    '''
    Execute query on the specified database (sid)
    sid
        The name of the database to execute the query on
    query
        The query to execute
    **connection_args
        Oracle Connection arguments
    '''

    ret = {}
    global authorization_modes
    if connection_mode is not None:
       mode = authorization_modes[connection_mode]
    else:
       mode = None
    #connection_args.update({'connection_sid': sid, 'connection_mode': cx_Oracle.SYSDBA})
    connection_args.update({'connection_sid': sid, 'connection_mode': mode})
    conn = _connect(**connection_args)

    if conn is None:
       return ret

    start = time.time()
    log.debug('Using db: %s to run query %s', sid, query)

    cur = conn.cursor()
    try:
        cur.execute(query)
        affected = cur.rowcount
        log.debug(query)
    except cx_Oracle.DatabaseError as err:
        query_error= '{}: {}'.format(query, err)
        __context__['devops_oracle.error'] = query_error
        log.error(err)
        return ret

    select_keywords = ["SELECT", "SHOW", "DESC"]
    select_query = False
    for keyword in select_keywords:
        if query.upper().strip().startswith(keyword):
           select_query = True
           break
    '''
    alter_keywords = ["ALTER"]
    alter_query = False
    for keyword in alter_keywords:
        if query.upper().strip().startswith(keyword):
           alter_query = True
           break
    '''

    if select_query:
       results = cur.fetchall()
       elapsed = (time.time() - start)
       if elapsed < 0.200:
          elapsed_h = str(round(elapsed * 1000, 1)) + 'ms'
       else:
          elapsed_h = str(round(elapsed, 2)) + 's'
       ret['query time'] = {'human': elapsed_h, 'raw': str(round(elapsed, 5))}
       ret['rows returned'] = affected
       columns = ()
       for column in cur.description:
           columns += (column[0],)
       ret['columns'] = columns
       ret['result'] = results
       return ret
    else:
       ret['rows affected'] = affected
       #ret["result"] = True
       return ret
    return ret

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def get_temporary_tablespace_nonasm(sid, **connection_args):

    '''
    Return temporary table list of non-asm database
    sid
        The name of the database to execute the query of temporary tablespace
    **connection_args
        Oracle Connection arguments
    '''
    ret = []

    query = 'SELECT name FROM v$asm_diskgroup'
    response = run_query(sid, query, **connection_args)

    #if not response['result']:
    if not response.get('result'):
        query = 'select name from v$tempfile'
        tempfile_response = run_query(sid, query, **connection_args)
        if tempfile_response['result']:
           return reduce(lambda x,y:x+y,tempfile_response['result'])
    return ret

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def get_instance_status(sid, **connection_args):

    '''
    Return status of oracle instance as below
    STARTED
    MOUNTED
    OPEN
    OPEN MIGRATE
    '''
    query = 'select STATUS from v$instance'
    response = run_query(sid, query, **connection_args)
    if response.get('result'):
       return response['result']
    return False

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def get_database_status(sid, **connection_args):

    '''
    Return status of oracle database as below
    ACTIVE
    SUSPENDED
    INSTANCE RECOVERY
    '''
    query = 'select DATABASE_STATUS from v$instance'
    response = run_query(sid, query, **connection_args)
    if response.get('result'):
       return response['result']
    return False

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def version(sid, **connection_args):

    '''
    Return the version of a Oracle server
    '''

    query = 'select VERSION from v$instance'
    response = run_query(sid, query, **connection_args)
    if response.get('result'):
       return response['result']
    return False

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def get_instnace_mode(sid, **connection_args):

    '''
    Return mode of oracle instance as below
    ALLOWED:  Allowing logins by all users
    RESTRICTED: Allowing logins by database administrators only
    '''
    query = 'select logins from v$instance'
    response = run_query(sid, query, **connection_args)
    if response.get('result'):
       return response['result']
    return False

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def get_oradata(sid, asm=False, **connection_args):

    '''
    This function is not required for now
    sid
        The name of the database to execute the query of dba files
    **connection_args
        Oracle Connection arguments
    '''

    if asm == False:
      query = 'SELECT distinct SUBSTR(file_name, 1, INSTR(file_name, '/', -1, 1)) ORADATA from dba_data_files'
    else:
      query = 'SELECT distinct SUBSTR(file_name, 1, INSTR(file_name, '/', 1, 2 ) - 1) AS ORADATA from dba_data_files'

    response = run_query(sid, query, **connection_args)

    if response.get('result'):
       return response['result']
    return None

def _disable_block_change_tracking(sid, **connection_args):

    '''
    This function is written to avoid oracle ORA-19755 error
    This function could be removed, if latest database support creation of Block change tracking file.
    If you use Block Change Tracking on your production database and try to duplicate it
    The problem is caused by the block change tracking file entry that exists in the target controlfile (on Production DB directory structure),
    but Oracle can't find the file because the new directory structure on the auxiliary server changes.

    After the restore and recovery of the auxiliary database, the duplicate process tries to open the DB
    but the bct file doesnt exist and the error is thrown.

    Block Change Tracking and Duplicate: avoid ORA-19755
    http://www.ludovicocaldara.net/dba/bct-duplicate-avoid-ora19755/

    Oracle note says that this bug is fixed in 12.1, but below line doesn't work
    Try below RMAN line for lateset oracle version before "duplicate database" line
    Non-ASM:
        SET NEWNAME FOR BLOCK CHANGE TRACKING FILE TO '/oradata/TESTDB/block_change.bct';
    ASM:
        SET NEWNAME FOR BLOCK CHANGE TRACKING FILE TO '+DATA';
    '''

    def _disable_bct(sid, **connection_args):
        connection_args.update({'connection_sid': sid, 'connection_mode': cx_Oracle.SYSDBA})
        conn = _connect(**connection_args)

        cur = conn.cursor()

        try:
           status, = cur.execute('select status from v$instance').fetchone()
        except DatabaseError as err:
           log.error('cannot select status: %s', err)
           return False

        if status in ['MOUNTED', 'OPEN']:
           try:
              bctstat, = cur.execute('select status from V$BLOCK_CHANGE_TRACKING').fetchone()
              # Nothing wrong with BCT
              return True
           except DatabaseError as err:
              # Oracle can't open BCT file
              pass

           try:
              cur.execute('alter database disable block change tracking')
              # BCT disabled
              return True
           except DatabaseError as err:
              log.error('disable block change tracking: %s', err)
              return False

        return False

    while not _disable_bct(sid, **connection_args):
       gevent.sleep(0)

    log.info('Block change tracking sucessfully disabled!')

def restoredb_from_backup_location(sid, backup_dir, oradata, newname='default', **connection_args):

    '''
    Restore a DB from RMAN backup location
    sid
        The name of the database to restore
    backup_dir
        RMAN backup directory location to restore a database
    oradata
        Directory location of oracle database files
    newname
        set newname for database datafiles and tempfiles
    **connection_args
        Oracle Connection arguments

    %d is ORACLE_SID
    %I is DBID
    %N is the tablespace name
    %f is the absolute datafile number

    set newname for block change tracking file doesn't work unfortunately.
    '''

    '''
    if not os.path.exists(backup_dir):
       log.error('Backup folder "%s" does not exist', backup_dir)
       return False
    '''

    if not _is_oracle_home_set():
       return False

    query = 'select instance_name from v$instance'
    response = run_query(sid, query, **connection_args)

    if not response.get('result'):
       log.error('Can not query instance_name: {}'.format(query))
       return False

    non_asm = get_temporary_tablespace_nonasm(sid, **connection_args)

    if non_asm:
       script = '''
       connect auxiliary {user}/{password}@{auxiliary_dsn}
       run {{
           set newname for database to '{newname}';
           duplicate database to {auxiliary_sid} noopen nofilenamecheck
           undo tablespace UNDOTBS1
           logfile group 1 ('{redo01a}', '{redo01b}') size 4M reuse,
           group 2 ('{redo02a}', '{redo02b}') size 4M reuse
           backup location '{backupset_dir}';
       }}
       '''
    else:
       script = '''
       connect auxiliary {user}/{password}@{auxiliary_dsn}
       run {{
           duplicate database to {auxiliary_sid} noopen nofilenamecheck
           undo tablespace UNDOTBS1
           logfile group 1 ('{redo01a}', '{redo01b}') size 4M reuse,
           group 2 ('{redo02a}', '{redo02b}') size 4M reuse
           backup location '{backupset_dir}';
       }}
       '''
    script = script.format(
        user=connargs['user'],
        password=connargs['pass'],
        auxiliary_dsn=connargs['dsn'],
        newname=os.path.join(oradata, '{}_D-%d_TS-%N_FNO-%f'.format(newname)),
        auxiliary_sid=sid,
        redo01a=os.path.join(oradata, 'redo01a.log'),
        redo01b=os.path.join(oradata, 'redo01b.log'),
        redo02a=os.path.join(oradata, 'redo02a.log'),
        redo02b=os.path.join(oradata, 'redo02b.log'),
        backupset_dir=backup_dir,
    )

    # avoid ORA-19755 bug
    if non_asm:
       bct_let = Greenlet.spawn(_disable_block_change_tracking, sid, **connection_args)

    # Run RMAN Script
    rman_let = Greenlet.spawn(execute_script, script)
    rman_let.join()

    if non_asm:
       bct_let.join(timeout=5)
    return rman_let.value

def backup(sid, backup_dir, full_backup=False, **connection_args):

    '''
    Backup a DB to RMAN backup location
    sid
        The name of the database to backup
    backup_dir
        RMAN backup directory location to backup a database
    full_backup
        Default is False. If True then full backup is taken at backup location
    **connection_args
        Oracle Connection arguments
    '''

    if not _is_oracle_home_set():
       return False

    query = 'select recid from v$backup_datafile where incremental_level = 0'
    response = run_query(sid, query, **connection_args)

    if not response.has_key("result"):
       log.error('Can not run query {}'.format(query))
       return False

    if full_backup:
       level = 0
    else:
       level = 0 if not response['result'] else 1

    script = '''
    connect target {user}/{password}@{target_dsn}
    CONFIGURE CONTROLFILE AUTOBACKUP FORMAT FOR DEVICE TYPE DISK TO '{autobackup_format}';
    run {{
        backup as compressed backupset
            incremental level {level}
            database
            include current controlfile
            format '{backupset_dir}';
    }}
    '''
    script = script.format(
        user=connargs['user'],
        password=connargs['pass'],
        target_dsn=connargs['dsn'],
        autobackup_format=os.path.join(backup_dir, '%F'),
        level=level,
        backupset_dir=os.path.join(backup_dir, '%U'),
    )

    log.debug(script)

    # avoid ORA-19755 bug
    #bct_let = Greenlet.spawn(_disable_block_change_tracking, **connection_args)

    # Run RMAN script
    rman_let = Greenlet.spawn(execute_script, script)

    rman_let.join()
    # bct_let.join(timeout=5)

    return rman_let.value


def execute_script(sid, script, action, connection_mode='SYSDBA', **connection_args):

    '''
    Execute RMAN script
    script
        Executing a set of commands youve placed into a script
    remote_target
        if True then remote connection string will be appended to script
    **connection_args
        if remote_target is True then oracle connection_args will be considered
    '''

    # sys passsowrd in Salt logs
    # log.debug(script)

    global rman_authorization_modes
    global rman_action
    conn_args = dict()

    if connection_mode is not None:
       mode = rman_authorization_modes[connection_mode]

    try:
       database_type = rman_action[action]
    except KeyError:
       log.error('restore and backup action supported only')
       return False

    if not _is_oracle_home_set():
       return False

    try:
       dsn      = '{0}:{1}/{2}'.format(connection_args['connection_host'], connection_args['connection_port'], sid)
       user     = connection_args['connection_user']
       password = connection_args['connection_pass']
    except KeyError:
       log.error('Some database connections arguments are missing')
       return False

    remote_conn = 'connect {database_type} "{user}/{password}@{target_dsn} as {connect_mode}"\n'
    remote_conn = remote_conn.format(database_type=database_type, user=user, password=password, target_dsn=dsn, connect_mode=mode)

    script = remote_conn + script

    oracle_home = os.environ.get('ORACLE_HOME')
    env={'ORACLE_HOME': oracle_home, 'PATH': os.path.join(oracle_home, 'bin')}

    log.debug(script)
    log.debug(remote_conn)
    try:
        proc = gevent.subprocess.Popen(args=['rman'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
    except OSError as err:
        log.debug('cannot start RMAN: {}'.format(err))
        return False

    proc.stdin.write(script)
    proc.stdin.close()

    proc.stdout.close()
    proc.wait()

    if proc.returncode != 0:
       log.debug('RMAN failed with return code {}'.format(proc.returncode))
       return False

    return True

def check_db_exists(sid, oracle_home=os.environ.get("ORACLE_HOME")):

    '''
    Return True if DB exists in /etc/oratab
    sid
        The name of the database to backup
    oracle_home
        Directory location of oracle home

    Check if the database exists in /etc/oratab
    Run only if you are running this salt state on oracle VM,
    if you are executing this state from remote VM then pass check_db_exists: False to other salt states
    '''
    existing_dbs = []
    oratab_file = '/etc/oratab'

    if not oracle_home:
       log.info('Oracle home is not set')
       return False

    if os.path.exists(oratab_file):
       with open(oratab_file) as oratab:
            for line in oratab:
                if line.startswith('#') or line.startswith(' '):
                   continue
                elif re.search(sid +':', line):
                   existing_dbs.append(line)
    if not existing_dbs:
       log.info('Oracle {0} is not present'.format(oratab_file))
       # Database /etc/oratab file doesn't exist
       return False
    else:
       for dbs in existing_dbs:
           if sid != '':
              if '%s:' % sid in dbs:
                 if dbs.split(':')[1] != oracle_home.rstrip('/'):
                    # Database is created, but with a different ORACLE_HOME
                    log.info('Database {} exists in a different ORACLE_HOME {}'.format(sid, dbs.split(':')[1]))
                    return False
                 elif dbs.split(':')[1] == oracle_home.rstrip('/'):
                    # Database already exist
                    log.info('Database {} exists in ORACLE_HOME {}'.format(sid, oracle_home))
                    return True
    log.info('Database {} does not exists in ORACLE_HOME {}'.format(sid, oracle_home))
    return False

@depends('cx_Oracle', fallback_function=_cx_oracle_req)
def client_version():

    '''
    Oracle Client Version
    Make sure ORACLE_HOME is set
    CLI Example:
    .. code-block:: bash
        salt '*' devops_oracle.client_version
    '''
    return '.'.join((six.text_type(x) for x in cx_Oracle.clientversion()))

def show_env():

    '''
    Show Environment used by Oracle Client
    CLI Example:
    .. code-block:: bash
        salt '*' devops_oracle.show_env
    .. note::
        at first _connect() ``NLS_LANG`` will forced to '.AL32UTF8'
    '''
    envs = ['PATH', 'ORACLE_HOME', 'TNS_ADMIN', 'NLS_LANG']
    result = {}
    for env in envs:
        if env in os.environ:
            result[env] = os.environ[env]
    return result
