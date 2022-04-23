for(let t of document.getElementsByClassName("copy-btn"))t.addEventListener("click",async()=>{await navigator.clipboard.writeText(t.getAttribute("value")).then(()=>{t.innerText="Copied!",setTimeout(()=>{t.innerText=t.getAttribute("data-reset")},1e3)},e=>alert(`Could not copy:
`+e.toString()))});
