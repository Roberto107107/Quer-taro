"use strict";
document.addEventListener("DOMContentLoaded", () => {
    const date = document.getElementById("adminCurrentDate");
    if (date) date.textContent = new Date().toLocaleDateString("es-MX", {dateStyle: "long"});
    document.querySelectorAll("form[data-confirm]").forEach(form => {
        form.addEventListener("submit", event => {
            if (!window.confirm(form.dataset.confirm)) event.preventDefault();
        });
    });
});
