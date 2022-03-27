import esbuild from "esbuild";

await esbuild.build({
    entryPoints: ["static/js/code-editor.ts"],
    outfile: "dist/js/code-editor.js",
    bundle: true,
    minify: true,
    format: "esm",
    logLevel: "debug",
    platform: "browser"
})