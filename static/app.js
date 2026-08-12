document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const input = button.parentElement.querySelector("input");
            const willShow = input.type === "password";
            input.type = willShow ? "text" : "password";
            button.textContent = willShow ? "隠す" : "表示";
            button.setAttribute("aria-label", willShow ? "パスワードを隠す" : "パスワードを表示");
        });
    });

    document.querySelectorAll(".flash-close").forEach((button) => {
        button.addEventListener("click", () => {
            const flash = button.closest(".flash");
            flash.classList.add("is-closing");
            flash.addEventListener("animationend", () => flash.remove(), { once: true });
        });
    });

    document.querySelectorAll(".flash[data-autohide]").forEach((flash) => {
        window.setTimeout(() => {
            if (!flash.isConnected || flash.classList.contains("is-closing")) return;
            flash.classList.add("is-closing");
            flash.addEventListener("animationend", () => flash.remove(), { once: true });
        }, 3500);
    });

    const quickAdd = document.querySelector("#quick-add");
    quickAdd?.addEventListener("toggle", () => {
        if (quickAdd.open) quickAdd.querySelector("input[name='name']")?.focus();
    });

    const editDrawer = document.querySelector("#edit-drawer");
    const editForm = editDrawer?.querySelector("[data-edit-form]");
    document.querySelectorAll("[data-open-editor]").forEach((button) => {
        button.addEventListener("click", () => {
            editForm.action = `/edit/${button.dataset.taskId}`;
            editForm.elements.name.value = button.dataset.taskName;
            editForm.elements.category_id.value = button.dataset.taskCategory;
            editForm.elements.deadline.value = button.dataset.taskDeadline;
            editDrawer.showModal();
            editForm.elements.name.focus();
        });
    });

    editDrawer?.querySelectorAll("[data-close-drawer]").forEach((button) => {
        button.addEventListener("click", () => editDrawer.close());
    });

    editDrawer?.addEventListener("click", (event) => {
        if (event.target === editDrawer) editDrawer.close();
    });

    const deleteDialog = document.querySelector("#delete-dialog");
    let pendingForm = null;
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (form.dataset.confirmed === "true") return;
            event.preventDefault();
            pendingForm = form;
            deleteDialog.querySelector("[data-dialog-task]").textContent = form.dataset.confirm;
            deleteDialog.showModal();
        });
    });

    deleteDialog?.addEventListener("close", () => {
        if (deleteDialog.returnValue === "confirm" && pendingForm) {
            pendingForm.dataset.confirmed = "true";
            pendingForm.requestSubmit();
        }
        pendingForm = null;
    });

    deleteDialog?.addEventListener("click", (event) => {
        if (event.target === deleteDialog) deleteDialog.close("cancel");
    });
});

// タスク追加画面の外側をクリックしたら閉じる
const quickAdd = document.querySelector("#quick-add");

document.addEventListener("click", (event) => {
    if (!quickAdd || !quickAdd.open) {
        return;
    }

    if (!quickAdd.contains(event.target)) {
        quickAdd.removeAttribute("open");
    }
});

// Escキーでも閉じられるようにする
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && quickAdd?.open) {
        quickAdd.removeAttribute("open");
    }
});
