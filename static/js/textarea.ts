for (let textarea of document.getElementsByTagName("textarea")) {
    textarea.addEventListener("input", function () {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight+'px';
        textarea.style.maxHeight = textarea.style.height
    });
}
