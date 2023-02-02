window.htmx = require("htmx.org");

document.body.addEventListener("htmx:beforeSwap", function(e) {
    switch(e.detail.xhr.status) {
        case 413:  // Request too large, doesn't contain HTML and needs manual treatment
            let input = document.querySelector("input[type=file]");
            let feedback = input.nextElementSibling;
            if(feedback == null || !feedback.classList.contains("invalid-feedback")) {
                feedback = document.createElement("div");
                feedback.classList.add("invalid-feedback");
                input.insertAdjacentElement("afterend", feedback);
            }
            feedback.innerText = "You uploaded a document that is too large (max. 100 MB)."
            input.classList.add("is-invalid");
            break;
        case 422:  // Validation exception
            e.detail.shouldSwap = true;
            e.detail.isError = false;
            break;
    }
});
