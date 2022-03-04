import esbuild from "esbuild";
import fs from "fs"
import { PurgeCSS } from "purgecss"
import sass from "sass"

const dev = process.argv.includes("-w") || process.argv.includes("--watch")

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
    if (f !== "bulma.css") all.push("static/css/" + f)
});

console.log("Building...")
let result = await esbuild.build({
    entryPoints: all,
    outdir: "dist",
    bundle: true,
    watch: dev,
    minify: true,
    metafile: true,
    logLevel: "debug",
    sourcemap: dev,
    platform: "browser"
})

let text = await esbuild.analyzeMetafile(result.metafile, {
    verbose: true,
})
console.log(text)