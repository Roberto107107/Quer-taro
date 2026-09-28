"use strict";
// Sending uses normal POST/redirect, so messages persist even without JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    const history = document.getElementById("message-list");
    if (history) history.scrollTop = history.scrollHeight;
});
