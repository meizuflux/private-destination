for (let copyBtn of document.getElementsByClassName("copy-btn")) {
    copyBtn.addEventListener("click", async () => {
        await navigator.clipboard.writeText(document.getElementById(copyBtn.getAttribute("data-target")).href)
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
            (r) => alert('Could not copy note value:\n' + r.toString())
        )
    })
}
