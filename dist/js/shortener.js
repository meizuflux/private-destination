for(let t of document.getElementsByClassName("copy-btn")){let e=document.getElementById(t.dataset.target);t.addEventListener("click",async()=>{await navigator.clipboard.writeText(location.origin+"/"+e.getAttribute("value")).then(()=>{t.innerText="Copied!",t.classList.add("is-success"),t.classList.remove("is-info"),setTimeout(()=>{t.innerText="Copy",t.classList.remove("is-success"),t.classList.add("is-info")},1e3)},s=>alert(`Could not copy shortened URL:
`+s.toString()))})}