const getById = document.getElementById.bind(document)

const apiKey = getById("api-key") as HTMLInputElement
const showBtn = getById("toggle-show-api-key")

// Show Button
showBtn.addEventListener("click", () => {
    if (apiKey.type === "password") {
        apiKey.type = "text";
        showBtn.innerText = "Hide"
    } else {
        apiKey.type = "password";
        showBtn.innerText = "Show"
    }
})

const copyBtn = getById("copy-api-key")
copyBtn.addEventListener("click", () => {
    const el = document.createElement('textarea');
    el.value = apiKey.value;
    el.setAttribute('readonly', '');
    el.style.position = 'absolute';
    el.style.left = '-9999px';
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    
    copyBtn.innerText = "Copied!"
    setTimeout(() => copyBtn.innerText = "Copy", 1000)
})

// Modal open
for (const trigger of document.getElementsByClassName("js-modal-trigger")) {
    const target = getById(trigger.dataset.target)
    trigger.addEventListener("click", () => {
        target.classList.toggle("is-active")
    })
}

// Modal close
for (const close of document.getElementsByClassName("modal-background")) {
    const target = close.closest(".modal")
    close.addEventListener("click", () => {
        target.classList.remove("is-active")
        regenContent.classList.remove("is-hidden")
        regenSuccess.classList.add("is-hidden")
    })
}

// Regen API Key
const regenBtn = getById("regen-btn")
const regenContent = getById("regen-content")
const regenSuccess = getById("regen-success")

regenBtn.addEventListener("click", async () => {
    regenBtn.classList.toggle("is-loading")

    const res = await fetch("/api/auth/api_key", {
        method: "POST"
    })

    const json = await res.json()

    apiKey.value = json["api_key"]

    regenContent.classList.add("is-hidden")
    regenSuccess.classList.remove("is-hidden")
    regenBtn.classList.remove("is-loading")

    setTimeout(() => regenBtn.innerText = "Regenerate", 1000)
})

const deleteBtn = getById("delete-btn")
const deleteInput = getById("delete-username-input") as HTMLInputElement

deleteInput.addEventListener("input", (e) => {
    if (e.target.value === deleteInput.placeholder) {
        deleteBtn.removeAttribute("disabled")
    }
    else {
        deleteBtn.setAttribute("disabled", "true")
    }
})

