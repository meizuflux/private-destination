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
copyBtn.addEventListener("click", async () => {
    await navigator.clipboard.writeText(apiKey.value)
        .then(
        () => {
            copyBtn.innerText = "Copied!"
            copyBtn.classList.add("is-success")
            copyBtn.classList.remove("is-info")
            setTimeout(() => {
                copyBtn.innerText = "Copy"
                copyBtn.classList.remove("is-success")
                copyBtn.classList.add("is-info")
            }, 1000)
        },
        (r) => alert('Could not copy API Key:\n' + r.toString())
        )
})
