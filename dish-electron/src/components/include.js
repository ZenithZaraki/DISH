/**@type {string} */
const WEBROOT = (()=>{
    const up1 = (s) => s.slice(0,s.lastIndexOf('/'));
    return up1(up1(up1(document.location.pathname)));
})();
const MODROOT = `${WEBROOT}/modules`;

/**
 * @param {string} tag
 * @param {{classList:string[]?,children:Array<HTMLElement|string>?}&Record<string,string>} attrs
 * @returns {HTMLElement}
 */
function makeElement(tag, attrs) {
    const t = document.createElement(tag);
    for (const k in attrs) {
        if (k === "classList") {
            t.classList.add(...attrs[k]);
        } else if (k === "children") {
            t.append(...attrs[k]);
        } else {
            t[k] = attrs[k];
        }
    }
    return t;
}

class HTMLInclude extends HTMLElement {
    static observedAttributes = [];
    // prevents adding multiple instances of scripts/stylesheets
    static #included = new Set();

    constructor() {
        super();
    }

    connectedCallback() {
        const name = this.getAttribute("name");
        const root = this.getAttribute("root") || `components`;
        const componentSrc = `${WEBROOT}/${root}/${name}/${name}`;
        /**@type {{style:boolean,script:boolean,html:string?}} */
        const component = {
            style: false,
            script: false,
            html: null
        };
        new Promise(r0 => {
            let n = 3;
            const check = () => {if(n)return;r0();};
            fetch(`${componentSrc}.js`, {method:"HEAD"}).then(res => {
                component.script = true;
                n --;
                check();
            }).catch(() => {
                n --;
                check();
            });
            if (this.hasAttribute("notag")) {
                n --;
                check();
            } else if (this.hasAttribute("tagname")) {
                const pass = ` pass='${this.getAttribute("pass")}'`;
                component.html = `<${this.getAttribute("tagname")}${this.hasAttribute("pass")?pass:""}/>`;
                n --;
                check();
            } else {
                fetch(`${componentSrc}.html`).then(res => {
                    res.text().then(txt => {
                        component.html = txt;
                        n --;
                        check();
                    });
                }).catch(() => {
                    n --;
                    check();
                });
            }
            fetch(`${componentSrc}.css`, {method:"HEAD"}).then(res => {
                component.style = this.hasAttribute("global-css");
                n --;
                check();
            }).catch(() => {
                n --;
                check();
            });
        }).then(() => {
            if (!HTMLInclude.#included.has(name)) {
                HTMLInclude.#included.add(name);
                if (component.style) {
                    const e = document.createElement("link");
                    e.rel = "stylesheet";
                    e.type = "text/css";
                    e.href = `${componentSrc}.css`;
                    document.head.appendChild(e);
                }
                if (component.script) {
                    const e = document.createElement("script");
                    e.src = `${componentSrc}.js`;
                    document.head.appendChild(e);
                }
            }
            if (component.html) {
                const t = document.createElement("template");
                t.innerHTML = component.html;
                this.replaceWith(t.content);
            } else {
                this.remove();
            }
        });
    }
}

customElements.define("x-include", HTMLInclude);

class SupportsPassthrough extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        if (this.hasAttribute("pass")) {
            const p = JSON.parse(this.getAttribute("pass"));
            for (const k in p) {
                this.setAttribute(k, p[k]);
            }
        }
    }
}
