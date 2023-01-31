window.htmx = require("htmx.org");

document.body.addEventListener("htmx:beforeSwap", function(e) {
    if(e.detail.xhr.status === 422) {
        e.detail.shouldSwap = true;
        e.detail.isError = false;
    }
});