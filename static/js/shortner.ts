for (let copyBtn of <HTMLButtonElement[]>document.getElementsByClassName("copy-btn")) {
    let target = document.getElementById(copyBtn.dataset.target)
    copyBtn.addEventListener("click", async () => {
        await navigator.clipboard.writeText(location.origin + "/" + target.innerText)
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
            (r) => alert('Could not copy codeblock:\n' + r.toString())
        )
    })
}