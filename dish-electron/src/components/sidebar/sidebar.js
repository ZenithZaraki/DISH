
class Sidebar extends HTMLElement {
    /**@type {HTMLTemplateElement} */
    static #content;
    static #compname = "sidebar";
    /**@type {typeof import("../../modules/api")} */
    static #api;
    static #ready = new Promise(r => {
        fetch(`${WEBROOT}/components/${this.#compname}/${this.#compname}.html`).then(async res => {
            this.#content = document.createElement("template");
            this.#content.innerHTML = await res.text();
            this.#api = await import(`${MODROOT}/api.js`);
            r();
        });
    });
    #root;
    constructor() {
        super();
        this.#root = this.attachShadow({mode:"closed"});
    }

    async connectedCallback() {
        await Sidebar.#ready;
        this.#root.appendChild(makeElement("link",{rel:"stylesheet",type:"text/css",href:`${WEBROOT}/components/${Sidebar.#compname}/${Sidebar.#compname}.css`}));
        this.#root.append(Sidebar.#content.content);
        const modSelect = this.#root.querySelector("select");
        /**@type {PolyPanel} */
        const main_panel = document.querySelector("div.mainzone > x-polypanel");
        /**@type {PolyPanel} */
        const controls_panel = this.#root.querySelector("x-polypanel");
        modSelect.onchange = async () => {
            main_panel.switchPanel(modSelect.value);
            controls_panel.switchPanel("&no-tools");
            controls_panel.switchPanel(`mod-${modSelect.value}`);
        };
        Sidebar.#api.fetchModuleRegistry().then(reg => {
            console.log(reg);
            for (const k in reg) {
                modSelect.appendChild(makeElement("option",{value:k,textContent:reg[k].display_name??k}));
                main_panel.appendChild(makeElement("x-pp-panel",{pid:k,textContent:`polypanel for module '${k}'`}));
            }
        });
    }
}

customElements.define("x-sidebar", Sidebar);

