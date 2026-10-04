// Adds an eye button to every password box so people can check what they typed.
document.querySelectorAll('input[type="password"]').forEach(function (input) {

    let group = input.parentElement;

    if (!group.classList.contains("input-group")) {
        group = document.createElement("div");
        group.className = "input-group" + (input.classList.contains("form-control-sm") ? " input-group-sm" : "");
        input.parentNode.insertBefore(group, input);
        group.appendChild(input);
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-outline-secondary";
    button.setAttribute("aria-label", "Show password");
    button.innerHTML = '<i class="bi bi-eye" aria-hidden="true"></i>';

    button.addEventListener("click", function () {
        const showing = input.type === "text";
        input.type = showing ? "password" : "text";
        button.querySelector("i").className = showing ? "bi bi-eye" : "bi bi-eye-slash";
        button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
        input.focus();
    });

    group.appendChild(button);
});
