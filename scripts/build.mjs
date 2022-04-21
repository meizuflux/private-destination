import esbuild from "esbuild";
import fs from "fs"
import sass from "sass-embedded"

let all = [];

const result = await sass.compileAsync("static/css/custom-bulma.scss")
fs.writeFile("static/css/bulma.css", result.css, (err) => err)

fs.readdirSync("./static/js").forEach(f => {
    all.push("static/js/" + f)
});

fs.readdirSync("./static/css").forEach(f => {
    if (f != "custom-bulma.scss") all.push("static/css/" + f)
});

await esbuild.build({
    entryPoints: all,
    outdir: "dist",
    bundle: true,
    minify: true,
    format: "esm",
    logLevel: "debug",
    platform: "browser",
})

