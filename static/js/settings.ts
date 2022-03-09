const holder = document.getElementById("api-key") as HTMLInputElement
const toggler = document.getElementById("toggle-show-api-key")

toggler.addEventListener("click", () => {
    if (holder.type === "password") {
        holder.type = "text";
        toggler.innerText = "Hide"
    } else {
        holder.type = "password";
        toggler.innerText = "Show"
    }
})

const copyButton = document.getElementById("copy-api-key")
copyButton.addEventListener("click", () => {
    const el = document.createElement('textarea');
    el.value = holder.value;
    el.setAttribute('readonly', '');
    el.style.position = 'absolute';
    el.style.left = '-9999px';
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    
    copyButton.innerText = "Copied!"
    setTimeout(function() {
        copyButton.innerText = "Copy"
    }, 1000)
})

const regenBtn = document.getElementById("regen-btn")
const regenContent = document.getElementById("regen-content")
const regenSuccess = document.getElementById("regen-success")

regenBtn.addEventListener("click", async () => {
    regenBtn.classList.toggle("is-loading")

    const res = await fetch("/api/auth/api_key", {
        method: "POST"
    })

    const json = await res.json()

    holder.value = json["api_key"]

    regenContent.classList.add("is-hidden")
    regenSuccess.classList.remove("is-hidden")
    regenBtn.classList.remove("is-loading")

    setTimeout(() => regenBtn.innerText = "Regenerate", 1000)
})

for (const trigger of document.getElementsByClassName("js-modal-trigger")) {
    const target = document.getElementById(trigger.dataset.target)
    trigger.addEventListener("click", () => {
        target.classList.toggle("is-active")
    })
}

for (const close of document.getElementsByClassName("modal-background")) {
    const target = close.closest(".modal")
    close.addEventListener("click", () => {
        target.classList.remove("is-active")
        regenContent.classList.remove("is-hidden")
        regenSuccess.classList.add("is-hidden")
    })
}