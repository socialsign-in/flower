from __future__ import absolute_import

import datetime
import time

from .search import satisfies_search_terms, parse_search_terms

from celery.events.state import Task
from celery.result import AsyncResult


"""
['result', 'uuid', 'clock', 'exchange', 'routing_key', 'failed', 'state', 'client', 'kwargs', 'sent', 'expires', 'retries', 'started', 'timestamp', 'args', 'worker', 'name', 'received', 'exception', 'revoked', 'succeeded', 'traceback', 'eta', 'retried', 'runtime']
"""

class BackendTaskObject():

    def __init__(self,task,event,state): 

        self._fields = Task._defaults.keys()
        for k in self._fields:
            setattr(self,k,None)
    
        if isinstance(task,AsyncResult):
            self.uuid = task.id
            self.result = task.result
            self.traceback = task.traceback 
            self.state = task.status
           
            if event:
                worker_host = event.get('hostname')
                self.name = event.get('task_name')
                self.worker = state.workers.get(worker_host) 
                self.exception = event.get('exception')
                self.clock = event.get('clock')
                self.timestamp = event.get('timestamp')
                self.args = event.get('args','N/A') 
                self.kwargs = event.get('kwargs','N/A') 
                self.retries = event.get('retries')

                if task.failed(): 
                    self.failed = event.get('timestamp')
                if task.successful(): 
                    self.succeeded = event.get('timestamp')
                    

                self.received = event.get('local_received')
     
                
        else:
            for k,v in task.iteritems():
                setattr(self,k,v)




def iter_tasks(events, limit=None, type=None, worker=None, state=None,
               sort_by=None, received_start=None, received_end=None,
               started_start=None, started_end=None, search=None):
    i = 0
    tasks = events.state.tasks_by_timestamp()
    if sort_by is not None:
        tasks = sort_tasks(tasks, sort_by)
    convert = lambda x: time.mktime(
        datetime.datetime.strptime(x, '%Y-%m-%d %H:%M').timetuple()
    )
    search_terms = parse_search_terms(search or {})

    for uuid, task in tasks:
        if type and task.name != type:
            continue
        if worker and task.worker and task.worker.hostname != worker:
            continue
        if state and task.state != state:
            continue
        if received_start and task.received and\
                task.received < convert(received_start):
            continue
        if received_end and task.received and\
                task.received > convert(received_end):
            continue
        if started_start and task.started and\
                task.started < convert(started_start):
            continue
        if started_end and task.started and\
                task.started > convert(started_end):
            continue
        if not satisfies_search_terms(task, search_terms):
            continue
        yield uuid, task
        i += 1
        if i == limit:
            break


sort_keys = {'name': str, 'state': str, 'received': float, 'started': float}


def sort_tasks(tasks, sort_by):
    assert sort_by.lstrip('-') in sort_keys
    reverse = False
    if sort_by.startswith('-'):
        sort_by = sort_by.lstrip('-')
        reverse = True
    for task in sorted(
            tasks,
            key=lambda x: getattr(x[1], sort_by) or sort_keys[sort_by](),
            reverse=reverse):
        yield task


def get_task_by_id(events, task_id):
    if hasattr(Task, '_fields'):  # Old version
        return events.state.tasks.get(task_id)
    else:
        _fields = Task._defaults.keys()
        task = events.state.tasks.get(task_id)
        if task is not None:
            task._fields = _fields
        return task

def get_task_from_backend(events, backend, task_id, event=None):
    _fields = Task._defaults.keys()
    task = AsyncResult(task_id,backend=backend)
    if task is not None:
        task = BackendTaskObject(task,event,events.state)

    return task



def as_dict(task):
    # as_dict is new in Celery 3.1.7
    if hasattr(Task, 'as_dict'):
        return task.as_dict()
    # old version
    else:
        return task.info(fields=task._defaults.keys())

