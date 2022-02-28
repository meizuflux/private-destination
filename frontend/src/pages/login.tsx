import { createSignal, For, Match, onMount, Switch } from "solid-js"

export default function Login() {
    const [providers, setProviders] = createSignal([])
    const [loading, setLoading] = createSignal(true)

    onMount(async () => {
        const res = await fetch("/api/auth/providers")

        const json = await res.json()
        setProviders(json)
        setLoading(false)
    })
    return (
        <Switch>
            <Match when={loading()}>
                <p>Loading login providers...</p>
            </Match>
            <Match when={loading() === false}>
                <For each={providers()} fallback={<div>Loading...</div>}>
                    {(item) => <a href={`/api/auth/login?provider=${item.key}`}>Login with {item.name}</a>}
                </For>
            </Match>
        </Switch>
    )
}