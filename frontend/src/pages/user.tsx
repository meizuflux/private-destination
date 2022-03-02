import { Match, onMount, Switch } from "solid-js"
import { redirect } from "../utils/redirect"
import { state, setState } from "../utils/auth"

export default function User() {
    console.log(state.user)

    onMount(async () => {
        if (state.user != {}) {
            const res = await fetch("/api/auth/@me")
            if (res.status == 401) {
                setState("user", {})
                return
            }

            const json = await res.json()
            setState("user", json)
        }
    })

    return (
        <Switch>
            <Match when={state.user === {}}>
                {redirect("/login")}
            </Match>
            <Match when={state.user}>
                <div>{JSON.stringify(state.user)}</div>
            </Match>
            <Match when={state.user == null}>
                <div>Loading user data</div>
            </Match>
        </Switch>
    )
}