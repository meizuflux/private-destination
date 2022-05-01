for (let copyBtn of <HTMLButtonElement[]>document.getElementsByClassName("copy-btn")) {
    copyBtn.addEventListener("click", async () => {
        await navigator.clipboard.writeText(copyBtn.getAttribute("value"))
        .then(
            () => {
                copyBtn.innerText = "Copied!"
                setTimeout(() => {
                    copyBtn.innerText = copyBtn.getAttribute("data-reset")
                }, 1000)
            },
            (r) => alert('Could not copy:\n' + r.toString())
        )
    })
}
