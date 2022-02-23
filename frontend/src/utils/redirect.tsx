import { Component } from "solid-js"


function redirect(location: string, type: string = "mouse") {
    if (type === "mouse") {
        window.location.href = location
    }
    if (type === "http") {
        window.location.replace(location)
    }
}

const wrappedRedirect = async (location: string, type: string = "mouse"): Promise<{ default: Component }> => {
    return {
        default: function() {
            redirect(location, type)
            return (
                <></>
            )
        }
    }
}

export {redirect, wrappedRedirect}