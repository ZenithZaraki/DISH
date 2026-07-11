
class DiagPanel extends HTMLElement {
    /**@type {HTMLTemplateElement} */
    static #content;
    static #compname = "diagpanel";
    static #ready = new Promise(r => {
        fetch(`${WEBROOT}/components/${this.#compname}/${this.#compname}.html`).then(async res => {
            this.#content = document.createElement("template");
            this.#content.innerHTML = await res.text();
            r();
        });
    });
    #root;#self;
    constructor() {
        super();
        this.#root = this.attachShadow({mode:"closed"});
        this.#self = DiagPanel;
    }

    async connectedCallback() {
        await this.#self.#ready;
        this.#root.appendChild(makeElement("link",{rel:"stylesheet",type:"text/css",href:`${WEBROOT}/components/${this.#self.#compname}/${this.#self.#compname}.css`}));
        this.#root.append(this.#self.#content.content);
    }
}

customElements.define("x-diagpanel", DiagPanel);

