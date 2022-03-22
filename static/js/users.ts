for (let user of document.getElementsByClassName("users-table-row")) {
    const user_id = parseInt(user.id)

    const buttons = user.lastElementChild.firstElementChild as HTMLDivElement
    const authorizationBtn = buttons.firstElementChild as HTMLButtonElement
    const deleteBtn = buttons.lastElementChild

    authorizationBtn.addEventListener("click", async () => {
        const res = await fetch(`/api/users/${user_id}/${authorizationBtn.innerText === "Authorize" ? "authorize" : "unauthorize"}`)

        location.reload()
    })

    deleteBtn.addEventListener("click", async () => {
        const res = await fetch(`/api/users/${user_id}/delete`)

        user.remove()
    })
}