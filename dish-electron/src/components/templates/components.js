/**
 * @file
 * this file contains templates for common styles of components
 */


/**
 * a component with isolated css and html, not accessible from outside and with no effects on the outside
 */
class ISOLATED extends HTMLElement {
    /**@type {HTMLTemplateElement} */
    static #content;
    static #compname = "ISOLATED";
    static #path = "components";
    static #ready = new Promise(r => {
        fetch(`${WEBROOT}/${this.#path}/${this.#compname}/${this.#compname}.html`).then(async res => {
            this.#content = document.createElement("template");
            this.#content.innerHTML = await res.text();
            r();
        });
    });
    #root;#self;
    constructor() {
        super();
        this.#root = this.attachShadow({mode:"closed"});
        this.#self = ISOLATED;
    }

    async connectedCallback() {
        await this.#self.#ready;
        this.#root.appendChild(makeElement("link",{rel:"stylesheet",type:"text/css",href:`${WEBROOT}/${this.#self.#path}/${this.#self.#compname}/${this.#self.#compname}.css`}));
        this.#root.append(this.#self.#content.content);
    }
}

