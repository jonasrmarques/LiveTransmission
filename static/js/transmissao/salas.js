/**
 * Room UI — consumes /api/transmissao/* and WebSocket signaling.
 * WebRTC media is handled by TransmissaoWebRTC (not mixed into business APIs).
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
    const headers = { Accept: "application/json" };
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

  function showSuccess(el, message) {
    if (!el) return;
    el.hidden = false;
    el.textContent = message;
  }

  function bindCriarForm(form) {
    const errorEl = document.getElementById("criar-sala-error");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideError(errorEl);
      const data = Object.fromEntries(new FormData(form).entries());
      try {
        const sala = await api("/api/transmissao/salas/", {
          method: "POST",
          form,
          body: { nome: data.nome },
        });
        window.location.href = `/transmissao/sala/${sala.identificador}/`;
      } catch (err) {
        showError(errorEl, formatDrfErrors(err.payload) || err.message);
      }
    });
  }

  function bindEntrarForm(form) {
    const errorEl = document.getElementById("entrar-sala-error");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideError(errorEl);
      const data = Object.fromEntries(new FormData(form).entries());
      try {
        const sala = await api("/api/transmissao/salas/entrar/", {
          method: "POST",
          form,
          body: { codigo: data.codigo },
        });
        window.location.href = `/transmissao/sala/${sala.identificador}/`;
      } catch (err) {
        showError(errorEl, formatDrfErrors(err.payload) || err.message);
      }
    });
  }

  function renderSala(sala) {
    document.getElementById("sala-nome").textContent = sala.nome;
    document.getElementById("sala-status").textContent = sala.status;
    document.getElementById("sala-codigo").textContent = sala.codigo_convite;

    const linkEl = document.getElementById("sala-link");
    const invitePath = `/transmissao/entrar/?codigo=${encodeURIComponent(sala.codigo_convite)}`;
    linkEl.href = invitePath;
    linkEl.textContent = window.location.origin + invitePath;

    renderParticipantes(sala.participantes || [], sala.is_owner, sala.status);
  }

  function initials(name) {
    const parts = String(name || "?").trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  function avatarColor(seed) {
    const colors = ["#5865f2", "#57f287", "#fee75c", "#eb459e", "#ed4245", "#00a8fc"];
    let hash = 0;
    String(seed || "").split("").forEach((ch) => {
      hash = (hash + ch.charCodeAt(0)) % colors.length;
    });
    return colors[hash];
  }

  function participantId(p) {
    return p.usuario_id || p.user_id || (p.usuario && p.usuario.id) || null;
  }

  function renderParticipantes(participantes, isOwner, status, onlineIds) {
    const list = document.getElementById("sala-participantes");
    const countEl = document.getElementById("participant-count");
    list.innerHTML = "";
    if (countEl) countEl.textContent = String(participantes.length);

    participantes.forEach((p) => {
      const username = p.username || (p.usuario && p.usuario.username) || "usuário";
      const id = participantId(p);
      const li = document.createElement("li");
      const isOnline = onlineIds ? onlineIds.has(Number(id)) : false;
      li.className = "member-item" + (isOnline ? " is-online" : "");
      li.dataset.userId = id || "";

      const avatar = document.createElement("span");
      avatar.className = "member-avatar";
      avatar.textContent = initials(username);
      avatar.style.background = avatarColor(username);

      const meta = document.createElement("div");
      meta.className = "member-meta";
      const nameEl = document.createElement("span");
      nameEl.className = "member-name";
      nameEl.textContent = username;
      const roleEl = document.createElement("span");
      roleEl.className = "member-role";
      roleEl.textContent = p.is_owner ? "Proprietário" : isOnline ? "Online" : "Na sala";
      meta.appendChild(nameEl);
      meta.appendChild(roleEl);

      li.appendChild(avatar);
      li.appendChild(meta);
      list.appendChild(li);
    });

    const ownerControls = document.getElementById("owner-controls");
    if (ownerControls) {
      if (isOwner) {
        ownerControls.hidden = false;
        const encerrar = document.getElementById("btn-encerrar");
        const compartilhar = document.getElementById("btn-compartilhar");
        if (encerrar) encerrar.disabled = status === "encerrada";
        if (compartilhar) compartilhar.disabled = status === "encerrada";
      } else {
        ownerControls.hidden = true;
      }
    }
  }

  function renderRoomState(event, currentUserIsOwner, onlineIds) {
    const room = event.room;
    document.getElementById("sala-nome").textContent = room.nome;
    document.getElementById("sala-status").textContent = room.status;
    document.getElementById("sala-codigo").textContent = room.codigo_convite;
    renderParticipantes(
      event.participantes || [],
      currentUserIsOwner,
      room.status,
      onlineIds
    );
  }

  function appendEventLog(message) {
    const log = document.getElementById("sala-eventos");
    if (!log) return;
    const li = document.createElement("li");
    li.textContent = message;
    log.prepend(li);
    while (log.children.length > 12) {
      log.removeChild(log.lastChild);
    }
  }

  function describeEvent(event) {
    const user = event.user ? event.user.username : "Usuário";
    switch (event.type) {
      case "presence.online":
        return `${user} conectou ao tempo real`;
      case "presence.offline":
        return `${user} desconectou do tempo real`;
      case "participant.joined":
        return `${user} entrou na sala`;
      case "participant.left":
        return `${user} saiu da sala`;
      case "transmission.started":
        return "Sessão de transmissão liberada";
      case "transmission.ended":
        return "Sala encerrada";
      case "participant.removed":
        return "Participante removido";
      case "stream.started":
        return "Compartilhamento de tela iniciado";
      case "stream.stopped":
        return "Compartilhamento de tela parado";
      default:
        return null;
    }
  }

  function setMediaHint(text) {
    const hint = document.getElementById("media-hint");
    if (hint) hint.textContent = text;
  }

  function setAudioTip(text, visible) {
    const tip = document.getElementById("media-audio-tip");
    if (!tip) return;
    tip.hidden = !visible;
    tip.textContent = text || "";
  }

  function showAudioActions({ showUnmute }) {
    const box = document.getElementById("media-audio-actions");
    const unmuteBtn = document.getElementById("btn-ativar-audio");
    if (!box) return;
    box.hidden = !showUnmute;
    if (unmuteBtn) unmuteBtn.hidden = !showUnmute;
  }

  async function playWithAudio(videoEl) {
    if (!videoEl) return false;
    videoEl.muted = false;
    videoEl.volume = 1;
    try {
      await videoEl.play();
      return !videoEl.paused;
    } catch (_) {
      // Autoplay with sound often blocked until a click.
      videoEl.muted = true;
      try {
        await videoEl.play();
      } catch (__) {
        /* ignore */
      }
      return false;
    }
  }

  function showLocalPreview(stream, meta) {
    const localVideo = document.getElementById("local-preview");
    const remoteVideo = document.getElementById("remote-player");
    remoteVideo.hidden = true;
    remoteVideo.srcObject = null;
    localVideo.srcObject = stream;
    // Always muted locally to avoid echo; viewers hear the stream.
    localVideo.muted = true;
    localVideo.hidden = false;
    localVideo.play().catch(() => {});

    const hasAudio = meta && meta.hasAudio;
    const hasDisplayAudio = meta && meta.hasDisplayAudio;
    if (!hasAudio) {
      setMediaHint("Compartilhando vídeo sem áudio.");
      setAudioTip(
        "Tela inteira no Linux/Chrome normalmente não envia som do sistema. Para áudio do vídeo: compartilhe uma ABA e marque “Compartilhar áudio”.",
        true
      );
    } else if (!hasDisplayAudio) {
      setMediaHint("Compartilhando sem áudio da tela.");
      setAudioTip(
        "Para som do vídeo/jogo, compartilhe uma aba do Chrome e marque “Compartilhar áudio”.",
        true
      );
    } else {
      setMediaHint("Você está compartilhando.");
      setAudioTip("", false);
    }
    showAudioActions({ showUnmute: false });
  }

  function showRemoteStream(stream) {
    const localVideo = document.getElementById("local-preview");
    const remoteVideo = document.getElementById("remote-player");
    if (localVideo) {
      localVideo.hidden = true;
      localVideo.srcObject = null;
    }
    remoteVideo.srcObject = stream;
    remoteVideo.hidden = false;
    setMediaHint("Recebendo transmissão…");

    const audioCount = stream.getAudioTracks().length;
    const videoCount = stream.getVideoTracks().length;

    playWithAudio(remoteVideo).then((audioOk) => {
      if (videoCount === 0 && audioCount === 0) {
        setMediaHint("Conectado, mas sem mídia ainda…");
        setAudioTip("Aguardando tracks de vídeo/áudio do apresentador.", true);
        showAudioActions({ showUnmute: false });
        return;
      }
      if (audioCount === 0) {
        setMediaHint("Assistindo (sem áudio no stream).");
        setAudioTip(
          "O apresentador precisa compartilhar uma aba com “Compartilhar áudio” marcado.",
          true
        );
        showAudioActions({ showUnmute: false });
      } else if (!audioOk) {
        setMediaHint("Assistindo — clique em “Ativar áudio”.");
        setAudioTip("O navegador bloqueou o áudio automático. Clique no botão abaixo.", true);
        showAudioActions({ showUnmute: true });
      } else {
        setMediaHint("Assistindo à transmissão.");
        setAudioTip("", false);
        showAudioActions({ showUnmute: false });
      }
    });
  }

  function clearMedia() {
    const localVideo = document.getElementById("local-preview");
    const remoteVideo = document.getElementById("remote-player");
    if (localVideo) {
      localVideo.srcObject = null;
      localVideo.hidden = true;
    }
    if (remoteVideo) {
      remoteVideo.srcObject = null;
      remoteVideo.hidden = true;
    }
    setMediaHint("Aguardando compartilhamento de tela…");
    setAudioTip("", false);
    showAudioActions({ showUnmute: false });
  }

  function showViewerWaiting() {
    const localVideo = document.getElementById("local-preview");
    const remoteVideo = document.getElementById("remote-player");
    if (localVideo) {
      localVideo.hidden = true;
      localVideo.srcObject = null;
    }
    if (remoteVideo) {
      remoteVideo.hidden = true;
      remoteVideo.srcObject = null;
    }
    setMediaHint("Conectando à transmissão…");
    setAudioTip("Se nada aparecer em alguns segundos, peça ao apresentador para clicar em Compartilhar tela novamente.", true);
    showAudioActions({ showUnmute: false });
  }

  function updateShareButtons(isSharing) {
    const shareBtn = document.getElementById("btn-compartilhar");
    const stopBtn = document.getElementById("btn-parar-stream");
    if (shareBtn) shareBtn.disabled = isSharing;
    if (stopBtn) stopBtn.disabled = !isSharing;
  }

  function bindSalaPage(root) {
    const salaId = root.dataset.salaId;
    const userId = Number(root.dataset.userId);
    const loadingEl = document.getElementById("sala-loading");
    const contentEl = document.getElementById("sala-content");
    const errorEl = document.getElementById("sala-error");
    const successEl = document.getElementById("sala-success");
    const wsStatusEl = document.getElementById("ws-status");
    const form = root.querySelector("form") || document.querySelector("form");
    let currentSala = null;
    let roomSocket = null;
    let webrtcSession = null;
    let participantesCache = [];
    const onlineIds = new Set([userId]);

    function refreshMembers() {
      if (!currentSala) return;
      renderParticipantes(
        participantesCache,
        currentSala.is_owner,
        currentSala.status,
        onlineIds
      );
    }

    function sendSignal(payload) {
      if (roomSocket) roomSocket.send(payload);
    }

    function ensureWebRtcSession() {
      if (webrtcSession || !window.TransmissaoWebRTC || !currentSala) return webrtcSession;

      webrtcSession = TransmissaoWebRTC.createSession({
        userId,
        isOwner: !!currentSala.is_owner,
        ownerId: currentSala.proprietario_id,
        sendSignal,
        onLocalStream: (stream, meta) => {
          showLocalPreview(stream, meta);
          updateShareButtons(true);
        },
        onRemoteStream: (stream) => {
          showRemoteStream(stream);
        },
        onStreamStopped: () => {
          clearMedia();
          updateShareButtons(false);
        },
        onError: (err) => {
          showError(errorEl, err.message || "Erro WebRTC.");
        },
        onLog: (message) => appendEventLog(message),
      });
      return webrtcSession;
    }

    function askForStream(reason) {
      const session = ensureWebRtcSession();
      if (!session || !currentSala || currentSala.is_owner) return;
      showViewerWaiting();
      appendEventLog(reason || "Pedindo stream ao apresentador…");
      session.requestStream();
      // Retry once in case the first ready arrived before the presenter finished setup.
      window.setTimeout(() => {
        if (session && !document.getElementById("remote-player").srcObject) {
          session.requestStream();
        }
      }, 2000);
    }

    async function loadSala() {
      hideError(errorEl);
      if (successEl) {
        successEl.hidden = true;
        successEl.textContent = "";
      }
      const sala = await api(`/api/transmissao/salas/${salaId}/`);
      currentSala = sala;
      participantesCache = sala.participantes || [];
      renderSala(sala);
      refreshMembers();
      loadingEl.hidden = true;
      contentEl.hidden = false;
      ensureWebRtcSession();
      connectWebSocket();
      return sala;
    }

    function connectWebSocket() {
      if (!window.TransmissaoWebSocket) return;
      if (roomSocket) roomSocket.close();

      roomSocket = TransmissaoWebSocket.connectRoomSocket(salaId, {
        onOpen() {
          if (wsStatusEl) wsStatusEl.textContent = "conectado";
          ensureWebRtcSession();
          if (currentSala && !currentSala.is_owner && currentSala.status === "transmitindo") {
            askForStream("Sala já em transmissão — solicitando mídia…");
          }
        },
        onClose(voluntary) {
          if (wsStatusEl) {
            wsStatusEl.textContent = voluntary ? "desconectado" : "reconectando…";
          }
        },
        onError() {
          if (wsStatusEl) wsStatusEl.textContent = "erro";
        },
        onMessage(event) {
          if (event.type === "room.state" && currentSala) {
            currentSala.status = event.room.status;
            currentSala.proprietario_id = event.room.proprietario_id;
            participantesCache = event.participantes || [];
            renderRoomState(event, currentSala.is_owner, onlineIds);
          }

          if (event.type === "presence.online" && event.user) {
            onlineIds.add(Number(event.user.id));
            refreshMembers();
          }
          if (event.type === "presence.offline" && event.user) {
            onlineIds.delete(Number(event.user.id));
            refreshMembers();
          }

          const text = describeEvent(event);
          if (text) appendEventLog(text);

          if (event.type === "stream.started" && currentSala && !currentSala.is_owner) {
            showViewerWaiting();
          }

          const session = ensureWebRtcSession();
          if (session) session.handleSignal(event);

          if (event.type === "transmission.ended") {
            if (session) session.stopSharing({ notify: false });
            clearMedia();
            updateShareButtons(false);
            const encerrarBtn = document.getElementById("btn-encerrar");
            const compartilharBtn = document.getElementById("btn-compartilhar");
            if (encerrarBtn) encerrarBtn.disabled = true;
            if (compartilharBtn) compartilharBtn.disabled = true;
            if (currentSala) currentSala.status = "encerrada";
            setMediaHint("Sala encerrada. Clique em Sair para voltar.");
            showSuccess(successEl, "A sala foi encerrada.");
          }
        },
      });
    }

    loadSala().catch((err) => {
      loadingEl.textContent = formatDrfErrors(err.payload) || err.message;
    });

    document.getElementById("btn-sair").addEventListener("click", async () => {
      try {
        if (webrtcSession) webrtcSession.destroy();
        if (roomSocket) roomSocket.close();
        // Always try leave; API is idempotent if room already encerrada.
        await api(`/api/transmissao/salas/${salaId}/sair/`, {
          method: "POST",
          form,
        });
        window.location.href = "/";
      } catch (err) {
        // If leave fails after room closed, still leave the page.
        if (currentSala && currentSala.status === "encerrada") {
          window.location.href = "/";
          return;
        }
        showError(errorEl, formatDrfErrors(err.payload) || err.message);
      }
    });

    const shareBtn = document.getElementById("btn-compartilhar");
    if (shareBtn) {
      shareBtn.addEventListener("click", async () => {
        hideError(errorEl);
        try {
          if (currentSala.status === "aguardando") {
            const sala = await api(`/api/transmissao/salas/${salaId}/iniciar/`, {
              method: "POST",
              form,
            });
            currentSala = Object.assign(currentSala, sala);
            renderSala(currentSala);
          }
          const session = ensureWebRtcSession();
          await session.startSharing();
          showSuccess(successEl, "Compartilhamento iniciado.");
        } catch (err) {
          showError(
            errorEl,
            formatDrfErrors(err.payload) || err.message || "Não foi possível compartilhar a tela."
          );
        }
      });
    }

    const stopBtn = document.getElementById("btn-parar-stream");
    if (stopBtn) {
      stopBtn.addEventListener("click", () => {
        if (webrtcSession) webrtcSession.stopSharing({ notify: true });
        showSuccess(successEl, "Compartilhamento parado.");
      });
    }

    document.getElementById("btn-encerrar").addEventListener("click", async () => {
      if (!window.confirm("Encerrar a sala para todos?")) return;
      try {
        if (webrtcSession) webrtcSession.stopSharing({ notify: true });
        await api(`/api/transmissao/salas/${salaId}/encerrar/`, {
          method: "POST",
          form,
        });
        if (roomSocket) roomSocket.close();
        window.location.href = "/";
      } catch (err) {
        showError(errorEl, formatDrfErrors(err.payload) || err.message);
      }
    });

    const unmuteBtn = document.getElementById("btn-ativar-audio");
    if (unmuteBtn) {
      unmuteBtn.addEventListener("click", async () => {
        const remoteVideo = document.getElementById("remote-player");
        const ok = await playWithAudio(remoteVideo);
        if (ok) {
          setMediaHint("Assistindo à transmissão.");
          setAudioTip("", false);
          showAudioActions({ showUnmute: false });
        }
      });
    }

    const copyBtn = document.getElementById("btn-copiar-codigo");
    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        const code = document.getElementById("sala-codigo");
        if (!code) return;
        try {
          await navigator.clipboard.writeText(code.textContent.trim());
          showSuccess(successEl, "Código copiado.");
        } catch (_) {
          showError(errorEl, "Não foi possível copiar o código.");
        }
      });
    }
  }

  window.TransmissaoSalas = {
    api,
    bindCriarForm,
    bindEntrarForm,
    bindSalaPage,
  };
})(window);
