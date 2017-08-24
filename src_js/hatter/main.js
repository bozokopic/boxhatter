import bean from 'bean';

import r from 'hatter/renderer';
import * as util from 'hatter/util';
import * as common from 'hatter/common';
import * as vt from 'hatter/vt';

import 'static!static/index.html';
import 'style/main.scss';


function main() {
    let conn = new WebSocket(wsAddress);

    conn.onopen = () => {
        let root = document.body.appendChild(document.createElement('div'));
        let state = util.set('conn', conn, common.defaultState);
        r.init(root, state, vt.main);
    };

    conn.onclose = () => {
        alert("Disconnected from server");
    };

    conn.onerror = () => {
        alert("Couldn't connect to server");
    };

    conn.onmessage = (evt) => {
        try {
            let msg = JSON.parse(evt.data);
            common.processMsg(msg);
        } catch(e) {
            conn.close();
            throw e;
        }
    };
}


bean.on(window, 'load', main);
