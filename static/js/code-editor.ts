import {EditorState, EditorView, basicSetup} from "@codemirror/basic-setup"
import {javascript} from "@codemirror/lang-javascript"
import {python} from "@codemirror/lang-python"
import {css} from "@codemirror/lang-css"
import {json} from "@codemirror/lang-json"
import {rust} from "@codemirror/lang-rust"

let editor = new EditorView({
  state: EditorState.create({
    extensions: [
      basicSetup,
      javascript(),
      python(),
      css(),
      json(),
      rust()
    ]
  }),
  parent: document.getElementById("editor")
})