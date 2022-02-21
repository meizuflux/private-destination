import { onMount } from "solid-js";

export default function Protected() {
    onMount(async () => {
        const token = localStorage.getItem("token")
        if (token === null) {
            return
        }

        const res = await fetch("http://localhost:8000/auth/protected", {
            headers: {
                "Authorization": "Bearer " + token
            }
        })

        console.log(await res.json())
    })
}