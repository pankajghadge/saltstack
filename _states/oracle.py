# -*- coding: utf-8 -*-
'''
Written by: pankaj ghadge
Execution of Oracle queries
'''
from __future__ import absolute_import, print_function, unicode_literals
import os
import sys

# Import Salt libs
import salt.utils.files
import salt.utils.stringutils

# Import 3rd-party libs
from salt.ext import six

def __virtual__():
    '''
    Only load if the oracle module is available in __salt__
    '''
    return 'devops_oracle.run_query' in __salt__

def _get_oracle_error():
    '''
    Look in module context for a Oracle error.
    '''
    return sys.modules[__salt__['test.ping'].__module__].__context__.pop('devops_oracle.error', None)

def _get_error(ret, sid, oracle_home, check_db_exists):
    if not oracle_home:
       ret['result'] = None
       ret['comment'] = ('Oracle home is not set')

    # check if database exists
    if check_db_exists and not __salt__['devops_oracle.check_db_exists'](sid, oracle_home):
       ret['result'] = None
       ret['comment'] = ('Database {0} is not present').format(sid)

def unmount(name,
       sid,
       check_db_exists=False,
       **connection_args):

    '''
    Unmount the specified database (sid)
    name
        Used only as an ID
    sid
        The name of the database to unmount
    check_db_exists:
        The state run will check that the specified database exists (default=False)
        before running any queries or command
        Make sure you are runnning this state on oracle instance. Remote execution will not work
    '''

    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Database {0} is present'.format(sid)}

    oracle_home = os.environ.get('ORACLE_HOME')

    _get_error(ret, sid, oracle_home, check_db_exists)
    if not ret["result"]:
       return ret

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'Will Unmount the database {}'.format(sid)
       return ret

    query_result = __salt__['devops_oracle.unmount'](sid, **connection_args)

    err = _get_oracle_error()
    if err is not None:
        ret['comment'] = err
        ret['result'] = None
        return ret

    if not query_result.get("result"):
        ret['comment'] = query_result.get('comment') or 'Unable to unmount database {}'.format(sid)
        ret['result'] = None
        return ret

    ret['comment'] = 'Database {} unmounted'.format(sid)
    ret['changes']['call'] = "Performed unmount on database {}".format(sid)
    return ret

def shutdown_immediate(name,
                   sid,
                   connection_mode='SYSDBA',
                   check_db_exists=False,
                   **connection_args):

    '''
    Execute shutdown immediate command on the specified database (sid)
    name
        Used only as an ID
    sid
        The name of the database to run shutdown immediate command
    check_db_exists:
        The state run will check that the specified database exists (default=False)
        before running any queries or command
        Make sure you are runnning this state on oracle instance. Remote execution will not work
    '''

    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Database {0} is present'.format(sid)}

    oracle_home = os.environ.get('ORACLE_HOME')

    _get_error(ret, sid, oracle_home, check_db_exists)

    if not ret["result"]:
       return ret

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'Will shutdown the database {}'.format(sid)
       return ret

    query_result = __salt__['devops_oracle.shutdown_immediate'](sid, connection_mode, **connection_args)

    err = _get_oracle_error()
    if err is not None:
        ret['comment'] = err
        ret['result'] = None
        return ret

    if not query_result.get("result"):
        ret['comment'] = query_result.get('comment') or 'Unable to shutdown database {}'.format(sid)
        ret['result'] = None
        return ret

    ret['comment'] = 'Database {} shutdown complete'.format(sid)
    ret['changes']['first_call'] = 'Performed first shutdown call on database {}'.format(sid)
    ret['changes']['query'] = 'Executed: alter database close normal.\n Executed: alter database dismount'
    ret['changes']['last_call'] = 'Performed the final shutdown call on database {}'.format(sid)
    return ret

def shutdown_abort(name,
                   sid,
                   connection_mode='SYSDBA',
                   check_db_exists=False,
                   **connection_args):

    '''
    Execute shutdown abort command on the specified database (sid)
    name
        Used only as an ID
    sid
        The name of the database to run shutdown abort command
    check_db_exists:
        The state run will check that the specified database exists (default=False)
        before running any queries or command
        Make sure you are runnning this state on oracle instance. Remote execution will not work
    '''

    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Database {0} is present'.format(sid)}

    oracle_home = os.environ.get('ORACLE_HOME')

    _get_error(ret, sid, oracle_home, check_db_exists)

    if not ret["result"]:
       return ret

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'Will shutdown abort the database {}'.format(sid)
       return ret

    query_result = __salt__['devops_oracle.shutdown_abort'](sid, connection_mode, **connection_args)

    err = _get_oracle_error()
    if err is not None:
        ret['comment'] = err
        ret['result'] = None
        return ret

    if not query_result.get("result"):
        ret['comment'] = query_result.get('comment') or 'Unable to shutdown abort database {}'.format(sid)
        ret['result'] = None
        return ret

    ret['comment'] = 'Database {} shutdown abort complete'.format(sid)
    ret['changes']['call'] = 'Performed shutdown abort call on database {}'.format(sid)
    return ret

def startup(name,
            sid,
            force=False,
            restrict=False,
            pfile=None,
            connection_mode='SYSDBA',
            check_db_exists=False,
            **connection_args):

    '''
    Execute startup command on the specified database (sid)
    name
        Used only as an ID
    sid
        The name of the database to startup
    check_db_exists:
        The state run will check that the specified database exists (default=False)
        before running any queries or command
        Make sure you are runnning this state on oracle instance. Remote execution will not work
    '''

    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Database {0} is present'.format(sid)}

    oracle_home = os.environ.get('ORACLE_HOME')

    _get_error(ret, sid, oracle_home, check_db_exists)

    if not ret["result"]:
       return ret

    if __opts__['test']:
       ret['result'] = None
       ret['comment'] = 'Will start the database {}'.format(sid)
       return ret

    query_result = __salt__['devops_oracle.startup'](sid, force, restrict, pfile, connection_mode, **connection_args)

    err = _get_oracle_error()
    if err is not None:
        ret['comment'] = err
        ret['result'] = None
        return ret

    if not query_result.get("result"):
        ret['comment'] = query_result.get('comment') or 'Unable to startup database {}'.format(sid)
        ret['result'] = None
        return ret

    ret['comment'] = 'Database {} startup complete '.format(sid)
    ret['changes']['call'] = 'Performed startup call on database {}'.format(sid)
    ret['changes']['query_to_be_issued'] = 'Perform these queries in salt state to open the database {}:'.format(sid)
    ret['changes']['query_to_be_issued'] += '\n 1) alter database mount.'
    ret['changes']['query_to_be_issued'] += '\n 2) alter database open.'
    return ret

def run_query(name,
        sid,
        query,
        connection_mode=None,
        output=None,
        overwrite=True,
        check_db_exists=False,
        **connection_args):

    '''
    Execute query on the specified database (sid)
    name
        Used only as an ID
    sid
        The name of the database to execute the query on
    query
        The query to execute
    output
        the file to store results
        OR None: output to the result comment (default)
    check_db_exists:
        The state run will check that the specified database exists (default=False)
        before running any queries
        Make sure you are runnning this state on oracle instance. Remote execution will not work
    '''

    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Database {0} is present'.format(sid)}

    '''
    if not oracle_home:
        ret['result'] = None
        ret['comment'] = ('Oracle home is not set')
        return ret

    # check if database exists
    if check_db_exists and not __salt__['devops_oracle.check_db_exists'](sid, oracle_home):
        ret['result'] = None
        ret['comment'] = ('Database {0} is not present').format(sid)
        return ret
    '''
    oracle_home = os.environ.get('ORACLE_HOME')

    _get_error(ret, sid, oracle_home, check_db_exists)

    if not ret["result"]:
       return ret

    if output is not None:
        if not overwrite and os.path.isfile(output):
            ret['comment'] = 'No execution needed. File ' + output + ' already set'
            return ret
        elif __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'Query would execute, storing result in ' + 'file: ' + output
            return ret
    elif __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'Query would execute, not storing result'
        return ret

    query_result = __salt__['devops_oracle.run_query'](sid, query, connection_mode, **connection_args)
    mapped_results = []

    err = _get_oracle_error()
    if err is not None:
        ret['comment'] = err
        ret['result'] = False
        return ret

    if 'result' in query_result:
        for res in query_result['result']:
            mapped_line = {}
            for idx, col in enumerate(query_result['columns']):
                mapped_line[col] = res[idx]
            mapped_results.append(mapped_line)
        query_result['result'] = mapped_results
        ret['out'] = mapped_results

    ret['comment'] = six.text_type(query_result)

    if output is not None:
        ret['changes']['query'] = "Executed. Output into " + output
        with salt.utils.files.fopen(output, 'w') as output_file:
            if 'result' in query_result:
                for res in query_result['result']:
                    for col, val in six.iteritems(res):
                        output_file.write(salt.utils.stringutils.to_str(col + ':' + val + '\n'))
            else:
                if isinstance(query_result, six.text_type):
                    output_file.write(salt.utils.stringutils.to_str(query_result))
                else:
                    for col, val in six.iteritems(query_result):
                        output_file.write(salt.utils.stringutils.to_str('{0}:{1}\n'.format(col, val)))
    else:
        ret['changes']['query'] = "Executed"

    return ret
