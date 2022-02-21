const redirect = (location: string, type: string = "mouse"): void => {
    if (type === "mouse") {
        window.location.href = location
    }
    if (type === "http") {
        window.location.replace(location)
    }
    throw new Error("type must be one of 'mouse' or 'http'")
}

export {redirect}