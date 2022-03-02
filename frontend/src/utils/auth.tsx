import { createStore } from "solid-js/store"
import { redirect } from "./redirect"

const [state, setState] = createStore({ user: null })

export {
    state,
    setState
}