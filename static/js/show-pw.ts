const passwordInput = document.getElementById("password") as HTMLInputElement
const showPassword = document.getElementById("show-password") as HTMLInputElement
const showPasswordText = document.getElementById("show-password-text") as HTMLSpanElement

showPassword.addEventListener("click", () => {
    if (showPassword.checked === false) {
        passwordInput.type = "password"
        showPasswordText.innerText = "Show"
    } else {
        passwordInput.type = "text"
        showPasswordText.innerText = "Hide"
    }
})
