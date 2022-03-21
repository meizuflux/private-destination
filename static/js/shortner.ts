const urlRegex = new RegExp(/http(s)?:\/\/[-a-zA-Z0-9@:%_\+~#=]{1,256}\.[a-z]{2,6}[-a-zA-Z0-9@:%_\+.~#?&//=]*/)

const createForm = document.getElementById("create-form")
const createKeyHelp = document.getElementById("create-key-help")
const createUrlHelp = document.getElementById("create-url-help")

function badUrlInput(urlElem: HTMLInputElement) {
    urlElem.classList.add("is-danger")
    createUrlHelp.classList.add("is-danger")
    createUrlHelp.innerText = "Please enter a URL"
}

createForm.addEventListener("submit", async (e: SubmitEvent) => {
    e.preventDefault()
    const elements = e.target.elements as HTMLFormControlsCollection

    const [keyElem, urlElem] = [elements["create-key"], elements["create-url"]]
    let [key, url] = [keyElem.value, urlElem.value]

    if (url === "") {
        badUrlInput(urlElem)
        return
    }

    if ((!(url.startsWith("https://") || url.startsWith("http://")))) {
        url = "https://" + url
    }

    if (!urlRegex.test(url)) {
        badUrlInput(urlElem)
        return
    }

    const res = await fetch("/api/shortner", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "key": key,
            "destination": url
        })
    })


    if (res.ok) {
        location.reload()
    }

    // HTTP 409 Conflict (the key already exists)
    if (res.status == 409) {
        keyElem.classList.add("is-danger")
        createKeyHelp.classList.add("is-danger")
        createKeyHelp.innerText = "A shortened URL with this key already exists"
    }
})


for (let row of document.getElementsByClassName("shortner-table-row")) {
    const cells = row.querySelectorAll("td")

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
        text.innerHTML = `Click to confirm that you want to delete short URL with key <code>${key}</code> pointing to <code>${destination}</code> created on <code>${creationDate}</code>`
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