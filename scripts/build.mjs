import esbuild from "esbuild";
import fs from "fs"

let all = [];

fs.readdirSync("./static/js").forEach(f => {
    all.push("static/js/" + f)
});

fs.readdirSync("./static/css").forEach(f => {
    all.push("static/css/" + f)
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

