
class XButton extends SupportsPassthrough {
    /**@type {HTMLTemplateElement} */
    static #content;
    static #compname = "button";
    static #path = "components/std";
    /**@type {typeof import("../../../modules/api")} */
    static #api;
    static #ready = new Promise(r => {
        fetch(`${WEBROOT}/${this.#path}/${this.#compname}/${this.#compname}.html`).then(async res => {
            this.#content = document.createElement("template");
            this.#content.innerHTML = await res.text();
            this.#api = await import(`${WEBROOT}/modules/api.js`);
            r();
        });
    });
    #root;#self;#valid=true;#init=false;
    /**@type {HTMLButtonElement} */
    #b;
    static observedAttributes = ["routing-key","payload","text"];
    constructor() {
        super();
        this.#root = this.attachShadow({mode:"closed"});
        this.#self = XButton;
        this.invalid_text = "⚠️ Invalid Control";
        this.invalid_css = "opacity: 0.5; cursor: not-allowed;";
    }
    setValid(valid) {
        this.#valid = valid;
        this.#b.disabled = !valid;
        this.#b.style.cssText = valid ? "" : this.invalid_css;
        this.#b.textContent = valid ? this.getAttribute("text") || "Submit" : this.invalid_text;
    }

    async connectedCallback() {
        if (!this.#init) {
            this.#init = true;
            await this.#self.#ready;
            super.connectedCallback();
            this.#root.appendChild(makeElement("link",{rel:"stylesheet",type:"text/css",href:`${WEBROOT}/${this.#self.#path}/${this.#self.#compname}/${this.#self.#compname}.css`}));
            this.#root.append(this.#self.#content.content);
            this.#b = this.#root.querySelector("button");
            let requestLock = false;
            this.#b.onclick = async () => {
                if (requestLock) return;
                requestLock = true;
                try {
                    const res = await fetch(`${this.#self.#api.API_BASE}/api/run-command`, {method:"POST",headers:[['content-type','application/json']],body:JSON.stringify({command:this.getAttribute("routing-key"),value:JSON.parse(this.getAttribute("payload"))})});
                    if (!res.ok) {
                        throw new Error(`Server responded with status ${response.status}`);
                    }
                    this.dispatchEvent(new CustomEvent("trigger",{detail:{result:(await res.json()).result}}));
                } catch (E) {
                    this.dispatchEvent(new CustomEvent("error", {detail:{ error: E.message || 'Execution failed' }}));
                } finally {
                    requestLock = false;
                }
            };
        }
        this.setValid(this.getAttribute("routing-key")&&this.getAttribute("payload"));
    }
    attributeChangedCallback(name, oldVal, newVal) {
        if (!this.#b) return;
        switch (name) {
            case "routing-key": {
                if (!newVal) {
                    this.setValid(false);
                } else if (this.getAttribute("payload")) {
                    this.setValid(true);
                }
                break;
            }
            case "payload": {
                if (!newVal) {
                    this.setValid(false);
                } else if (this.getAttribute("routing-key")) {
                    this.setValid(true);
                }
                break;
            }
            case "text": {
                if (this.#valid) {
                    this.#b.textContent = newVal;
                }
                break;
            }
        }
    }
}
customElements.define("x-button", XButton);

