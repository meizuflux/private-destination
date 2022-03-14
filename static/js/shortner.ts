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