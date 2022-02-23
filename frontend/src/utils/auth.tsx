import { redirect } from "./redirect"

export default async (path: string) => {
    if (localStorage.getItem("token") === null) {
        redirect("/login")
        
    }
}