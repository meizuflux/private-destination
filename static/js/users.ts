for (let user of document.getElementsByClassName("users-table-row")) {
    const user_id = user.getAttribute("data-id")
    alert(user_id)

    const buttons = user.lastElementChild.firstElementChild as HTMLDivElement
    const authorizeBtn = buttons.firstElementChild
    const deleteBtn = buttons.lastElementChild

    authorizeBtn.addEventListener("click", async () => {
        alert(`/api/users/${user_id}/authorize`)
        const res = await fetch(`/api/users/${user_id}/authorize`)
        user.remove()
    })

    deleteBtn.addEventListener("click", async () => {
        const res = await fetch(`/api/users/${user_id}/delete`)
        user.remove()
    })
}