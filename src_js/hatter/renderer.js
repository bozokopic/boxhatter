import Delegator from 'dom-delegator';
import bean from 'bean';
import vh from 'virtual-dom/h';
import diff from 'virtual-dom/diff';
import patch from 'virtual-dom/patch';
import createElement from 'virtual-dom/create-element';

import * as u from 'hatter/util';


const delegator = Delegator();
const vhTypes = ['VirtualNode', 'Widget'];


function vhFromArray(node) {
    if (!node)
        return [];
    if (u.isString(node) || vhTypes.includes(node.type))
        return node;
    if (!u.isArray(node))
        throw 'Invalid node structure';
    if (node.length < 1)
        return [];
    if (typeof node[0] != 'string')
        return node.map(vhFromArray);
    let hasProps = (node.length > 1 &&
                    u.isObject(node[1]) &&
                    !vhTypes.includes(node[1].type));
    let children = Array.from(
            u.flatten(node.slice(hasProps ? 2 : 1).map(vhFromArray)));
    let result = hasProps ? vh(node[0], node[1], children) :
                            vh(node[0], children);
    return result;
}


class VTreeRenderer {

    constructor(el) {
        this._el = el;
        this._vtree = null;
    }

    render(vtree) {
        let vt = vhFromArray(vtree);
        if (vt.type == 'VirtualNode') {
            if (this._vtree) {
                let d = diff(this._vtree, vt);
                patch(this._el.firstChild, d);
            } else {
                while (this._el.firstChild)
                    this._el.removeChild(this._el.firstChild);
                this._el.appendChild(createElement(vt));
            }
            this._vtree = vt;
        } else {
            this._vtree = null;
            while (this._el.firstChild)
                this._el.removeChild(this._el.firstChild);
        }
    }

}


export class Renderer {

    constructor(el, initState, vtCb, maxFps) {
        this.init(el, initState, vtCb, maxFps);
    }

    init(el, initState, vtCb, maxFps) {
        this._state = null;
        this._changes = [];
        this._promise = null;
        this._timeout = null;
        this._lastRender = null;
        this._vtCb = vtCb;
        this._maxFps = maxFps;
        this._r = new VTreeRenderer(el || document.querySelector('body'));
        if (initState)
            this.change(_ => initState);
    }

    get(...paths) {
        return u.get(paths, this._state);
    }

    set(path, value) {
        if (arguments.length < 2) {
            value = path;
            path = [];
        }
        return this.change(path, _ => value);
    }

    change(path, cb) {
        if (arguments.length < 2) {
            cb = path;
            path = [];
        }
        this._changes.push([path, cb]);
        if (this._promise)
            return this._promise;
        this._promise = new Promise((resolve, reject) => {
            setTimeout(() => {
                try {
                    this._change();
                } catch(e) {
                    this._promise = null;
                    reject(e);
                    throw e;
                }
                this._promise = null;
                resolve();
            }, 0);
        });
        return this._promise;
    }

    _change() {
        let change = false;
        while (this._changes.length > 0) {
            let [path, cb] = this._changes.shift();
            let view = u.get(path);
            let oldState = this._state;
            this._state = u.change(path, cb, this._state);
            if (this._state && u.equals(view(oldState),
                                        view(this._state)))
                continue;
            change = true;
            if (!this._vtCb || this._timeout)
                continue;
            let delay = (!this._lastRender || !this._maxFps ?
                0 :
                (1000 / self._maxFps) -
                (performance.now() - this._lastRender));
            this._timeout = setTimeout(() => {
                this._timeout = null;
                this._lastRender = performance.now();
                this._r.render(this._vtCb(this._state));
                bean.fire(this, 'render', this._state);
            }, (delay > 0 ? delay : 0));
        }
        if (change)
            bean.fire(this, 'change', this._state);
    }

}


const defaultRenderer = new Renderer();
export default defaultRenderer;
