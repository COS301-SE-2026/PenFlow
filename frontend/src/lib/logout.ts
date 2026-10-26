export function submitLogout(): void {
    const form = document.createElement("form");

    form.method = "post";
    form.action = "/api/auth/logout";
    form.hidden = true;

    document.body.appendChild(form);
    form.submit();
}