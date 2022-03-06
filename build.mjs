import esbuild from "esbuild";
import fs from "fs"
import { PurgeCSS } from "purgecss"
import sass from "sass"

const bulma = sass.compile("node_modules/bulma/bulma.sass")

const purgeCSSResult = await new PurgeCSS().purge({
    content: ['templates/*.html'],
    css: [{raw: bulma.css}]
})

fs.writeFileSync("static/css/bulma.css", purgeCSSResult[0].css)

let all = [];

fs.readdirSync("./static/js").forEach(f => {
    all.push("static/js/" + f)
});

fs.readdirSync("./static/css").forEach(f => {
    all.push("static/css/" + f)
});

console.log("Building...")
await esbuild.build({
    entryPoints: all,
    outdir: "dist",
    bundle: true,
    minify: true,
    logLevel: "debug",
    platform: "browser",
})