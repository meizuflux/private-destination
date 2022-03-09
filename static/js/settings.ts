const holder = document.getElementById("apiKey") as HTMLInputElement
const toggler = document.getElementById("toggleShowApiKey")

toggler.addEventListener("click", () => {
    if (holder.type === "password") {
        holder.type = "text";
        toggler.innerText = "Hide"
    } else {
        holder.type = "password";
        toggler.innerText = "Show"
    }
})

const copyButton = document.getElementById("copyApiKey")

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

const regenBtn = document.getElementById("regenApiKey")

regenBtn.addEventListener("click", async () => {
    regenBtn.classList.toggle("is-loading")

    const res = await fetch("/api/auth/api_key", {
        method: "POST"
    })

    const json = await res.json()

    holder.value = json["api_key"]

    regenBtn.innerText = "Regenerated"

    regenBtn.classList.toggle("is-loading")

    setTimeout(() => regenBtn.innerText = "Regenerate", 1000)
})