
import r from 'hatter/renderer';
import * as util from 'hatter/util';


export const defaultState = {
    conn: null,
    log: {
        offset: 0,
        offsetText: '0',
        limit: 0,
        limitText: '0',
        entries: []
    },
    job: {
        active: null,
        queue: []
    },
    repositories: []
};


export function processMsg(msg) {
    if (msg.type == 'repositories') {
        r.set('repositories', msg.repositories);
    } else if (msg.type == 'active_job') {
        r.set(['job', 'active'], msg.job);
    } else if (msg.type == 'job_queue') {
        r.set(['job', 'queue'], msg.jobs);
    } else if (msg.type == 'log_entries') {
        r.set(['log', 'entires'], msg.entries);
    }
}


export function addJob(repository) {
    r.get('conn').send(JSON.stringify({
        type: 'add_job',
        repository: repository,
        commit: 'HEAD'
    }));
}


bean.on(r, 'change', state => {
    let newOffset = parseInt(state.log.offsetText);
    let newLimit = parseInt(state.log.limitText);
    if (util.isInteger(newOffset) && newOffset != state.log.offset) {
        r.set(['log', 'offset'], newOffset).then(sendSetLog);
    }
    if (util.isInteger(newLimit) && newLimit != state.log.limit) {
        r.set(['log', 'limit'], newLimit).then(sendSetLog);
    }
});


function sendSetLog() {
    let conn = r.get('conn');
    if (!conn)
        return;
    conn.send(JSON.stringify({
        type: 'set_log',
        offset: r.get('offset'),
        limit: r.get('limit')
    }));
}
