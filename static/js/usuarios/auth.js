/**
 * Auth UI helpers — talk only to /api/usuarios/* (session + CSRF).
 * Kept independent from Django template logic for a future React swap.
 */
(function (window) {
  "use strict";

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function csrfToken(form) {
    const input = form && form.querySelector('input[name="csrfmiddlewaretoken"]');
    return (input && input.value) || getCookie("csrftoken") || "";
  }

  async function api(path, { method = "GET", body, form } = {}) {
    const headers = {
      Accept: "application/json",
    };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      headers["X-CSRFToken"] = csrfToken(form);
    } else if (method !== "GET" && method !== "HEAD") {
      headers["X-CSRFToken"] = csrfToken(form);
    }

    const response = await fetch(path, {
      method,
      headers,
      credentials: "same-origin",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    let data = null;
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (_) {
        data = { detail: text };
      }
    }

    if (!response.ok) {
      const error = new Error((data && data.detail) || "Falha na requisição.");
      error.status = response.status;
      error.payload = data;
      throw error;
    }
    return data;
  }

  function showError(el, message) {
    if (!el) return;
    el.hidden = false;
    el.textContent = message;
  }

  function hideError(el) {
    if (!el) return;
    el.hidden = true;
    el.textContent = "";
  }

  function formatDrfErrors(payload) {
    if (!payload || typeof payload !== "object") return "Falha na requisição.";
    if (typeof payload.detail === "string") return payload.detail;
    const parts = [];
    Object.keys(payload).forEach((key) => {
      const value = payload[key];
      if (Array.isArray(value)) parts.push(value.join(" "));
      else if (typeof value === "string") parts.push(value);
    });
    return parts.join(" ") || "Falha na requisição.";
  }

  function bindCadastroForm(form) {
    if (!form) return;
    const errorEl = document.getElementById("cadastro-error");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideError(errorEl);
      const data = Object.fromEntries(new FormData(form).entries());
      try {
        await api("/api/usuarios/cadastro/", {
          method: "POST",
          form,
          body: {
            username: data.username,
            email: data.email,
            password: data.password,
            password_confirm: data.password_confirm,
          },
        });
        window.location.href = "/usuarios/login/";
      } catch (err) {
        showError(errorEl, formatDrfErrors(err.payload) || err.message);
      }
    });
  }

  function bindLoginForm(form) {
    if (!form) return;
    const errorEl = document.getElementById("login-error");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideError(errorEl);
      const data = Object.fromEntries(new FormData(form).entries());
      try {
        await api("/api/usuarios/login/", {
          method: "POST",
          form,
          body: {
            username: data.username,
            password: data.password,
          },
        });
        window.location.href = "/";
      } catch (err) {
        showError(errorEl, formatDrfErrors(err.payload) || err.message);
      }
    });
  }

  async function logout(form) {
    await api("/api/usuarios/logout/", { method: "POST", form });
    window.location.href = "/";
  }

  function bindPerfilPage({ loadingEl, contentEl, formEl, fields }) {
    (async () => {
      try {
        const user = await api("/api/usuarios/perfil/");
        if (fields.username) fields.username.textContent = user.username;
        if (fields.email) fields.email.textContent = user.email;
        if (fields.name) {
          const full = [user.first_name, user.last_name].filter(Boolean).join(" ");
          fields.name.textContent = full || "—";
        }
        if (fields.avatar) {
          const seed = user.username || "?";
          fields.avatar.textContent = seed.slice(0, 2).toUpperCase();
        }
        if (formEl) {
          formEl.email.value = user.email || "";
          formEl.first_name.value = user.first_name || "";
          formEl.last_name.value = user.last_name || "";
        }
        if (loadingEl) loadingEl.hidden = true;
        if (contentEl) contentEl.hidden = false;
      } catch (err) {
        if (loadingEl) {
          loadingEl.textContent = formatDrfErrors(err.payload) || err.message;
        }
      }
    })();

    if (!formEl) return;
    const errorEl = document.getElementById("perfil-error");
    const successEl = document.getElementById("perfil-success");
    formEl.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideError(errorEl);
      if (successEl) {
        successEl.hidden = true;
        successEl.textContent = "";
      }
      const data = Object.fromEntries(new FormData(formEl).entries());
      try {
        const user = await api("/api/usuarios/perfil/", {
          method: "PATCH",
          form: formEl,
          body: {
            email: data.email,
            first_name: data.first_name,
            last_name: data.last_name,
          },
        });
        if (fields.email) fields.email.textContent = user.email;
        if (fields.name) {
          const full = [user.first_name, user.last_name].filter(Boolean).join(" ");
          fields.name.textContent = full || "—";
        }
        if (successEl) {
          successEl.hidden = false;
          successEl.textContent = "Perfil atualizado.";
        }
      } catch (err) {
        showError(errorEl, formatDrfErrors(err.payload) || err.message);
      }
    });
  }

  window.UsuariosAuth = {
    api,
    logout,
    bindCadastroForm,
    bindLoginForm,
    bindPerfilPage,
  };
})(window);
