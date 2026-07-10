
class EULA extends HTMLElement {
    /**@type {HTMLTemplateElement} */
    static #content;
    /**@type {string} */
    static #lastModified;
    static #ready = new Promise(r => {
        fetch(`${WEBROOT}/components/eula/eula.html`).then(async res => {
            this.#content = document.createElement("template");
            this.#content.innerHTML = await res.text();
            try {
                this.#lastModified = (await fetch(`${WEBROOT}/../public/docs/DISH_EULA.html`, {method:"HEAD"})).headers.get("last-modified");
            } catch {
                this.#lastModified = 0;
            }
            r();
        });
    });
    #root;
    constructor() {
        super();
        this.#root = this.attachShadow({mode:"closed"});
        this.hidden = true;
    }

    async connectedCallback() {
        await EULA.#ready;
        this.#root.appendChild(makeElement("link",{rel:"stylesheet",type:"text/css",href:`${WEBROOT}/components/eula/eula.css`}));
        this.#root.append(EULA.#content.content);
        if (EULA.#lastModified === 0) {
            this.#root.querySelector(".eula-body").hidden = true;
            this.#root.querySelector(".eula-issue").hidden = false;
            this.hidden = false;
            return;
        }
        this.#root.querySelector(".accept-btn").onclick = () => {
            this.hidden = true;
            localStorage.setItem("eula-lastmodified", EULA.#lastModified);
        };
        this.#root.querySelector(".view-btn").onclick = () => {
            window.open(`${WEBROOT}/../public/docs/DISH_EULA.html?cb=${Date.now()}`, "_blank");
        };
        if (EULA.#lastModified !== localStorage.getItem("eula-lastmodified")) {
            this.hidden = false;
        }
    }
}

customElements.define("x-eula", EULA);

