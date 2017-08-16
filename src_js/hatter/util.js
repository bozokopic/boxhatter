

export const isArray = Array.isArray;
export const isObject = obj => obj !== null &&
                               typeof(obj) == 'object' &&
                               !isArray(obj);
export const isNumber = n => typeof(n) == 'number';
export const isInteger = Number.isInteger;
export const isString = str => typeof(str) == 'string';


export function clone(obj) {
    if (isArray(obj))
        return Array.from(obj, clone);
    if (isObject(obj)) {
        let ret = {};
        for (let i in obj)
            ret[i] = clone(obj[i]);
        return ret;
    }
    return obj;
}


export function equals(x, y) {
    if (x === y)
        return true;
    if (typeof(x) != 'object' || typeof(y) != 'object' || x === null || y === null)
        return false;
    if (Array.isArray(x) || Array.isArray(y)) {
        if (!Array.isArray(x) || !Array.isArray(y) || x.length != y.length)
            return false;
    }
    for (let i in x)
        if (!equals(x[i], y[i]))
            return false;
    for (let i in y)
        if (!equals(x[i], y[i]))
            return false;
    return true;
}


export function toPairs(obj) {
    return Object.entries(obj);
}


export function fromPairs(arr) {
    let ret = {};
    for (let [k, v] of arr)
        ret[k] = v;
    return ret;
}


export function* flatten(arr) {
    if (isArray(arr)) {
        for (let i of arr)
            if (isArray(i))
                yield* flatten(i);
            else
                yield i;
    } else {
        yield arr;
    }
}


export function pipe(...fns) {
    if (fns.length < 1)
        throw 'no functions';
    return function (...args) {
        let ret = fns[0].apply(this, args);
        for (let fn of fns.slice(1))
            ret = fn(ret);
        return ret;
    };
}


export function curry(fn) {
    let wrapper = function(oldArgs) {
        return function(...args) {
            args = oldArgs.concat(args);
            if (args.length >= fn.length)
                return fn.apply(this, args);
            return wrapper(args);
        };
    };
    return wrapper([]);
}


export const get = curry((path, obj) => {
    let ret = obj;
    for (let i of flatten(path)) {
        if (ret === null || typeof(ret) != 'object')
            return undefined;
        ret = ret[i];
    }
    return ret;
});


export const change = curry((path, fn, obj) => {
    function _change(path, obj) {
        if (isInteger(path[0])) {
            obj = (isArray(obj) ? Array.from(obj) : []);
        } else if (isString(path[0])) {
            obj = (isObject(obj) ? Object.assign({}, obj) : {});
        } else {
            throw 'invalid path';
        }
        if (path.length > 1) {
            obj[path[0]] = _change(path.slice(1), obj[path[0]]);
        } else {
            obj[path[0]] = fn(obj[path[0]]);
        }
        return obj;
    }
    path = Array.from(flatten(path));
    if (path.length < 1)
        return fn(obj);
    return _change(path, obj);
});


export const set = curry((path, val, obj) => change(path, _ => val, obj));


export const omit = curry((path, obj) => {
    function _omit(path, obj) {
        if (isInteger(path[0])) {
            obj = (isArray(obj) ? Array.from(obj) : []);
        } else if (isString(path[0])) {
            obj = (isObject(obj) ? Object.assign({}, obj) : {});
        } else {
            throw 'invalid path';
        }
        if (path.length > 1) {
            obj[path[0]] = _omit(path.slice(1), obj[path[0]]);
        } else {
            delete obj[path[0]];
        }
        return obj;
    }
    path = Array.from(flatten(path));
    if (path.length < 1)
        return undefined;
    return _omit(path, obj);
});


export const sortBy = curry((fn, arr) => Array.from(arr).sort((x, y) => {
    let xVal = fn(x);
    let yVal = fn(y);
    if (xVal < yVal)
        return -1;
    if (xVal > yVal)
        return 1;
    return 0;
}));


export const map = curry((fn, arr) => arr.map(fn));


export const filter = curry((fn, arr) => arr.filter(fn));


export const append = curry((val, arr) => arr.concat([val]));
