import { useParams, useSearchParams } from "solid-app-router"
import { createSignal, For, Match, onMount, Show, Switch } from "solid-js"

export default function Login() {
    const [providers, setProviders] = createSignal([])
    const [searchParams, _] = useSearchParams();


    onMount(async () => {
        const res = await fetch("/api/auth/providers")

        const json = await res.json()
        setProviders(json)
    })
    return (
        <div class="container has-text-centered">
                <div class="column is-4 is-offset-4"></div>
                    <Show when={searchParams.restricted}>
                        <article class="message is-danger is-medium">
                            <p class="message-header">
                                Restricted Access
                            </p>
                            <p class="message-body">
                                The route you were trying to access requires you to be logged in
                            </p>
                        </article>
                    </Show>
                    <h1 class="is-size-1">Login</h1>
                    <div class="buttons is-centered">
                        <For each={providers()} fallback={<><a class="button is-loading is-primary" /><a class="button is-loading is-primary" /></>}>
                            {(item) => (
                                <a class="button is-primary is-vertical" href={`/api/auth/login?provider=${item.key}`}>
                                    {searchParams.signup ? "Sign up" : "Login"} with {item.name}
                                </a>
                            )}
                        </For>
                    </div>
        </div>
    )
}