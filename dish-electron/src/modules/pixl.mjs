/**
 * @file
 * this file provides an implementation of an interpreter for PIXL (see "/docs/pixl.txt")
 */

/**
 * @param {string} c character to check
 * @returns {boolean}
 */
function isAsciiAlpha(c) {
    return (c>='a'&&c<='z')||(c>='A'&&c<='Z');
}
/**
 * @param {string} c character to check
 * @returns {boolean}
 */
function isAsciiDigit(c) {
    return c>='0'&&c<='9';
}
/**
 * @param {string} c character to check
 * @returns {boolean}
 */
function isAsciiHexDigit(c) {
    return (c>='0'&&c<='9')||(c>='a'&&c<='f')||(c>='A'&&c<='F');
}
/**
 * @param {string} c character to check
 * @returns {boolean}
 */
function isAsciiAlnum(c) {
    return isAsciiDigit(c)||isAsciiAlpha(c);
}
/**
 * @param {string} c character to check
 * @returns {boolean}
 */
function isAsciiIdent(c) {
    return c==='_'||isAsciiAlnum(c);
}
/**
 * @param {string} c character to check
 * @returns {boolean}
 */
function isAsciiWhitespace(c) {
    return (c>='\x09'&&c<='\x0d')||c===' '||c==='~';
}
/**
 * @param {string} c character to check
 * @returns {boolean}
 */
function isPIXLSymbol(c) {
    return "+-%^&|*(){}[]!=<>/:;.,".includes(c);
}
/**
 * all the valid combinations of characters that can make up a single "symbol" token
 */
const SYMBOL_UNITS = [
    '(',')','>','<','/','%','!','[',']','{','}',':',';','^','&','|','*','+','-','=','==','!=',
    '>=','<=','{(',')}',',','.'
];


/**@enum {number} */
const LexType = {
    SYMBOL: 0,
    IDENT: 1,
    INTEGER: 2,
    FLOAT: 3,
    STRING: 4,
    KEYWORD: 5,
    PARAM: 6
};
/**@typedef {{type:LexType,value:string}} LexToken */

/**@enum {number} */
const LexPossible = {
    // enum variants are ordered by decreasing precedence
    SYMBOL: 1,
    IDENT: 2,
    INTEGER: 4,
    FLOAT: 8,
    STRING: 16,
    KEYWORD: 32,
    PARAM: 64
};

/**@enum {number} */
const LexPSFlags = {
    SEEN_DOT: 1,
    SEEN_CLOSING: 2,
    SEEN_SEMI: 4
};

/**
 * @param {string} input
 * @param {boolean} inline
 * @returns {LexToken[]}
 */
export function lex(input, inline) {
    if (input.includes('"') || (inline && input.includes("'"))) {
        throw new SyntaxError("invalid PIXL syntax (innappropriate quotes)");
    }
    /**@type {LexToken[]} */
    const output = [];
    // current position in input
    let i = 0;
    // start of current token
    let tstart = 0;
    // possible types this token could have
    let possible = 0;
    // flags for things seen during parsing
    let pstate_flags = 0;
    /**
     * returns true if the token is finished
     * @returns {boolean}
     */
    const update_pstate = () => {
        const c = input[i];
        // not currently parsing a token
        if (tstart === i) {
            possible = 0;
            pstate_flags = 0;
            switch (c) {
                // a token starting with '#' can only be a string
                case '#': {
                    possible = LexPossible.STRING;
                    return;
                }
                // starting with '@' can only be a keyword
                case '@': {
                    possible = LexPossible.KEYWORD;
                    return;
                }
                // starting with '$' can only be an external parameter
                case '$': {
                    possible = LexPossible.PARAM;
                    return;
                }
                // can only be a numeric literal or an operator
                case '+':case '-': {
                    possible = LexPossible.INTEGER|LexPossible.FLOAT|LexPossible.SYMBOL;
                    return;
                }
                case ';': {
                    possible = LexPossible.SYMBOL;
                    pstate_flags = LexPSFlags.SEEN_SEMI;
                    return;
                }
                default: {
                    if (isAsciiDigit(c)) {
                        possible = LexPossible.INTEGER|LexPossible.FLOAT;
                        return;
                    }
                    if (isAsciiIdent(c)) {
                        possible = LexPossible.IDENT;
                        return;
                    }
                    if (isAsciiWhitespace(c)) {
                        return true;
                    }
                    possible = LexPossible.SYMBOL;
                    return;
                }
            }
        }
        const delta = i - tstart;
        switch (possible) {
            case LexPossible.STRING: {
                if (pstate_flags&LexPSFlags.SEEN_CLOSING) return true;
                if (c === '#') {
                    pstate_flags |= LexPSFlags.SEEN_CLOSING;
                }
                return;
            }
            case LexPossible.KEYWORD: {
                if (!isAsciiIdent(c)) return true;
                return;
            }
            case LexPossible.PARAM: {
                if (pstate_flags&LexPSFlags.SEEN_CLOSING) {
                    return true;
                }
                if (delta === 1) {
                    if (c === '(') return;
                    possible = 0;
                    return true;
                }
                if (c === ')') {
                    pstate_flags |= LexPSFlags.SEEN_CLOSING;
                    return;
                }
                if (c === '$') {
                    if (delta === 2) return;
                    possible = 0;
                    return true;
                }
                // ensure that c is a valid character for an external parameter name
                if (!isAsciiIdent(c)) {
                    switch (c) {
                        case'%':case'.':case'-':case'@':case'|':return;
                        default: {
                            possible = 0;
                            return true;
                        }
                    }
                }
                return;
            }
            case LexPossible.IDENT: {
                if (isAsciiIdent(c)) return;
                return true;
            }
            default: {
                if (c === ';' || pstate_flags&LexPSFlags.SEEN_SEMI) {
                    return true;
                }
                if (possible&LexPossible.SYMBOL) {
                    if (!isPIXLSymbol(c) || !SYMBOL_UNITS.includes(input.slice(tstart,i+1))) {
                        if (possible === LexPossible.SYMBOL) return true;
                        possible ^= LexPossible.SYMBOL;
                    }
                }
                // Float is never cleared before Integer, so this works to check both of them
                if (possible&LexPossible.FLOAT) {
                    if (!isAsciiDigit(c)) {
                        if (delta === 1) {
                            if (!possible&LexPossible.SYMBOL) {
                                possible = 0;
                                return true;
                            }
                            possible = LexPossible.SYMBOL;
                            return;
                        }
                        if (pstate_flags&LexPSFlags.SEEN_DOT) {
                            if (input[i-1] === '.') {
                                possible = 0;
                            }
                            return true;
                        }
                        if (c === '.') {
                            pstate_flags |= LexPSFlags.SEEN_DOT;
                            possible ^= LexPossible.INTEGER;
                            return;
                        }
                        return true;
                    }
                }
                return;
            }
        }
    };
    /**
     * @returns {LexType}
     */
    const pick_type = () => {
        for (const k in LexPossible) {
            const v = LexPossible[k];
            if (possible&v) return LexType[k];
        }
    };
    let _debug = false;
    while (i >= 0 && i < input.length) {
        if (input[i] === "'") { // skip comments
            // comments that do not have their own lines must come after a semicolon (';')
            if (possible) {
                throw new SyntaxError("comment appears without separation from previous token");
            }
            i = input.indexOf("\n", i);
            tstart = i;
            if (_debug) {
                console.log(`skipping comment, new position ${i}`);
            }
            continue;
        }
        if (i===tstart && input[i]==='~') {
            _debug = !_debug;
            i ++;
            tstart ++;
            continue;
        }
        if (update_pstate()) {
            if (_debug) {
                console.log(`(${tstart}->${i}) "${isAsciiWhitespace(input[i])?'x'+input.charCodeAt(i).toString(16).padStart(2,'0'):input[i]}" [${Object.keys(LexPossible).filter(v=>possible&LexPossible[v]).join(", ")}] [${pstate_flags.toString(2)}] EOT`);
            }
            if (!possible) {
                if (tstart === i && isAsciiWhitespace(input[i])) {
                    i ++;
                    tstart = i;
                    continue;
                }
                throw new SyntaxError(`invalid lexographic token (${input.slice(tstart, i)})`);
            }
            output.push({type:pick_type(),value:input.slice(tstart, i)});
            tstart = i;
            // continue without incrementing i because the current character is not part of the token that was just parsed
            // and must be reprocessed
            continue;
        } else if (_debug) {
            console.log(`(${tstart}->${i}) "${isAsciiWhitespace(input[i])?'x'+input.charCodeAt(i).toString(16).padStart(2,'0'):input[i]}" [${Object.keys(LexPossible).filter(v=>possible&LexPossible[v]).join(", ")}] [${pstate_flags.toString(2)}] CONT`);
        }
        i ++;
    }
    return output;
}

