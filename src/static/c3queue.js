document.querySelectorAll("form#event-filter input[type=checkbox]").forEach((checkbox) => {
    checkbox.addEventListener("change", (event) => {
        event.target.closest("form").submit();
    });
})
