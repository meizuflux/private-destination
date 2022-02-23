import { onMount } from "solid-js"
import { redirect } from "../utils/redirect";

export default function AuthCallback() {
    onMount(async () => {
        const fragment = new URLSearchParams(window.location.hash.slice(1))
        const [accessToken, tokenType] = [fragment.get('access_token'), fragment.get('token_type')];
        console.log(accessToken, tokenType)

        const options = {
            method: "POST",
            body: JSON.stringify({"token": accessToken}),
            headers: {'Content-Type': 'application/json'}
        }

		fetch("http://localhost:8000/auth/token", options)
			.then(result => result.json())
			.then(response => {
				console.log(response)
                localStorage.setItem("token", response["token"])
                localStorage.setItem("user", JSON.stringify(response["user"]))
			})
			.catch(console.error);
        
        redirect("/")
    })

    return (
        <p>Logging you in...</p>
    )
}