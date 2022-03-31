
for (let row of document.getElementsByClassName("shortner-table-row")) {
    const cells = row.querySelectorAll("td")

    const key = (cells[0].firstElementChild as HTMLLinkElement).innerText // enclosed inside a <a> tag
    const destination = (cells[1].firstElementChild as HTMLLinkElement).innerText // same as above
    const clicks = cells[2].innerText
    const creationDate = cells[3].innerText

    const btns = cells[4].firstElementChild.children as HTMLCollectionOf<HTMLButtonElement>
    
    const copyBtn = btns[0]
    const editBtn = btns[1]
    const deleteBtn = btns[2]

    copyBtn.addEventListener("click", () => {
        const el = document.createElement('textarea');
        el.value = location.origin + "/" + key;
        el.setAttribute('readonly', '');
        el.style.position = 'absolute';
        el.style.left = '-9999px';
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        
        copyBtn.innerText = "Copied!"
        copyBtn.classList.add("is-success")
        copyBtn.classList.remove("is-info")
        setTimeout(() => {
            copyBtn.innerText = "Copy"
            copyBtn.classList.remove("is-success")
            copyBtn.classList.add("is-info")
        }, 1000)
    })

    editBtn.addEventListener("click", async () => {
        alert("edited!")
    })

    deleteBtn.addEventListener("click", async () => {
        const modal = document.getElementById("delete-modal")
        const text = document.getElementById("delete-text")
        text.innerHTML = `Clicking this button will immediately delete short url with key <code>${key}</code> pointing to <code>${destination}</code> created on <code>${creationDate}</code>. You will no longer be able to use this and the key will be able to be taken by someone else.`
        modal.setAttribute("data-target", key)
        modal.classList.add("is-active")
    })
}

// Modal close
for (const close of document.getElementsByClassName("modal-background")) {
    const target = close.closest(".modal")
    close.addEventListener("click", () => {
        target.classList.remove("is-active")
    })
}

const modalDeleteBtn = document.getElementById("delete-btn")

modalDeleteBtn.addEventListener("click", async () => {
    const modal = modalDeleteBtn.closest(".modal")

    const id = modal.getAttribute("data-target")

    const target = document.getElementById(id)

    const res = await fetch(`/api/shortner/${encodeURIComponent(id)}`, {
        method: "DELETE"
    })

    console.log(await res.json())

    target.remove()

    modal.classList.remove("is-active")
})