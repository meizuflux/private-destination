import { Match, onMount, Switch } from "solid-js"
import { createStore } from "solid-js/store"
import { redirect } from "../utils/redirect"

export default function User() {
    const [state, setState] = createStore({user: {}})

    onMount(async () => {
        const res = await fetch("/api/auth/@me")
        if (res.status == 401) {
            setState("user", null)
            return
        }

        const json = await res.json()
        setState("user", json)
    })

    return (
        <Switch>
            <Match when={state.user === null}>
                {redirect("/login")}
            </Match>
            <Match when={state.user != {}}>
                <div>{JSON.stringify(state.user)}</div>
            </Match>
            <Match when={state.user == {}}>
                <div>Loading user data</div>
            </Match>
        </Switch>
    )
}