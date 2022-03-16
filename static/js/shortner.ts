const createForm = document.getElementById("create-form")
const createInput = document.getElementById("create-input") as HTMLInputElement
const createBtn = document.getElementById("create-btn") as HTMLButtonElement

const l = document.getElementById("logger")

createForm.addEventListener("submit", async (e) => {
    e.preventDefault()

    await fetch("/api/shortner", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "key": "",
            "destination": createInput.value
        })
    })

    location.reload()
})

for (let row of document.getElementsByClassName("shortner-table-row")) {
    const cells = row.querySelectorAll("td")

    const id = row.id
    const key = cells[0].firstElementChild.innerText // enclosed inside a <a> tag
    const destination = cells[1].firstElementChild.innerText // same as above
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
        setTimeout(() => copyBtn.innerText = "Copy", 1000)
    })

    editBtn.addEventListener("click", async () => {
        alert("edited!")
    })

    deleteBtn.addEventListener("click", async () => {
        const modal = document.getElementById("delete-modal")
        const text = document.getElementById("delete-text")
        text.innerHTML = `Click to confirm that you want to delete short URL with key <code>${key}</code> pointing to <code>${destination}</code> created on <code>${creationDate}</code>`
        modal.setAttribute("data-target", id)
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
    const target = document.getElementById(modal.getAttribute("data-target"))
    target.remove()

    modal.classList.remove("is-active")
})