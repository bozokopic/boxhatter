import bean from 'bean';
import R from 'ramda';

import r from 'hatter/renderer';
import * as l from 'hatter/lenses';
import * as common from 'hatter/common';
import * as vt from 'hatter/vt';

import 'static!static/index.html';
import 'style/main.scss';


function main() {
    let root = document.body.appendChild(document.createElement('div'));
    r.init(root, common.defaultState, vt.main);
}


bean.on(window, 'load', main);
