/**
 * P2P WebRTC session for screen + audio sharing.
 * Isolated from page templates; talks to WebSocket only for signaling.
 */
(function (window) {
  "use strict";

  const ICE_SERVERS = [{ urls: "stun:stun.l.google.com:19302" }];

  function toId(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function serializeSdp(description) {
    if (!description) return null;
    return { type: description.type, sdp: description.sdp };
  }

  function createSession({
    userId,
    isOwner,
    ownerId,
    sendSignal,
    onRemoteStream,
    onLocalStream,
    onStreamStopped,
    onError,
    onLog,
  }) {
    const peers = new Map(); // remoteUserId (number) -> { pc, pendingIce, makingOffer }
    let localStream = null;
    let micStream = null;
    let sharing = false;
    const selfId = toId(userId);
    const presenterId = toId(ownerId);

    function log(message) {
      if (onLog) onLog(message);
    }

    function emitError(err) {
      if (onError) onError(err);
    }

    function stopTracks(stream) {
      if (!stream) return;
      stream.getTracks().forEach((track) => track.stop());
    }

    function closePeer(remoteUserId) {
      const id = toId(remoteUserId);
      const entry = peers.get(id);
      if (!entry) return;
      entry.pc.onicecandidate = null;
      entry.pc.ontrack = null;
      entry.pc.onconnectionstatechange = null;
      entry.pc.close();
      peers.delete(id);
    }

    function closeAllPeers() {
      Array.from(peers.keys()).forEach(closePeer);
    }

    async function flushPendingIce(entry) {
      while (entry.pendingIce.length) {
        const candidate = entry.pendingIce.shift();
        try {
          await entry.pc.addIceCandidate(candidate);
        } catch (err) {
          log("ICE candidate ignorado: " + (err.message || err));
        }
      }
    }

    function createPeerConnection(remoteUserId) {
      const id = toId(remoteUserId);
      closePeer(id);

      const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
      const entry = { pc, pendingIce: [], makingOffer: false };
      let remoteStream = null;

      pc.onicecandidate = (event) => {
        if (!event.candidate) return;
        sendSignal({
          type: "webrtc.ice_candidate",
          target_user_id: id,
          payload: { candidate: event.candidate.toJSON() },
        });
      };

      pc.onconnectionstatechange = () => {
        log(`Peer ${id}: ${pc.connectionState}`);
        if (pc.connectionState === "failed") {
          // Ask again for a fresh offer/answer cycle.
          if (!isOwner) {
            requestStream();
          }
        }
        if (pc.connectionState === "closed") {
          closePeer(id);
        }
      };

      if (!isOwner) {
        pc.ontrack = (event) => {
          if (event.streams && event.streams[0]) {
            remoteStream = event.streams[0];
          } else {
            if (!remoteStream) remoteStream = new MediaStream();
            if (!remoteStream.getTrackById(event.track.id)) {
              remoteStream.addTrack(event.track);
            }
          }
          log(
            `Track remota recebida (${event.track.kind}). ` +
              `V=${remoteStream.getVideoTracks().length} A=${remoteStream.getAudioTracks().length}`
          );
          if (onRemoteStream) onRemoteStream(remoteStream);
        };
      }

      if (localStream) {
        localStream.getTracks().forEach((track) => {
          track.enabled = true;
          pc.addTrack(track, localStream);
        });
      }

      peers.set(id, entry);
      return entry;
    }

    async function createOfferFor(remoteUserId) {
      if (!sharing || !localStream) return;
      const id = toId(remoteUserId);
      if (id === null || id === selfId) return;

      const entry = createPeerConnection(id);
      entry.makingOffer = true;
      try {
        const offer = await entry.pc.createOffer({
          offerToReceiveAudio: false,
          offerToReceiveVideo: false,
        });
        await entry.pc.setLocalDescription(offer);
        sendSignal({
          type: "webrtc.offer",
          target_user_id: id,
          payload: { sdp: serializeSdp(entry.pc.localDescription) },
        });
        log(`Offer enviado para usuário ${id}`);
      } finally {
        entry.makingOffer = false;
      }
    }

    async function handleOffer(message) {
      if (isOwner) return;
      const senderId = toId(message.sender_id);
      if (senderId === null) return;

      const entry = createPeerConnection(senderId);
      const sdp = message.payload && message.payload.sdp;
      if (!sdp || !sdp.type || !sdp.sdp) {
        throw new Error("Offer SDP inválido.");
      }

      await entry.pc.setRemoteDescription(sdp);
      await flushPendingIce(entry);

      const answer = await entry.pc.createAnswer();
      await entry.pc.setLocalDescription(answer);
      sendSignal({
        type: "webrtc.answer",
        target_user_id: senderId,
        payload: { sdp: serializeSdp(entry.pc.localDescription) },
      });
      log("Answer enviado ao apresentador");
    }

    async function handleAnswer(message) {
      if (!isOwner) return;
      const senderId = toId(message.sender_id);
      const entry = peers.get(senderId);
      if (!entry) {
        log(`Answer de ${senderId} ignorado (peer inexistente).`);
        return;
      }
      const sdp = message.payload && message.payload.sdp;
      if (!sdp || !sdp.type || !sdp.sdp) {
        throw new Error("Answer SDP inválido.");
      }
      if (entry.pc.signalingState !== "have-local-offer") {
        log(`Answer ignorado (signalingState=${entry.pc.signalingState}).`);
        return;
      }
      await entry.pc.setRemoteDescription(sdp);
      await flushPendingIce(entry);
      log(`Answer aplicado do usuário ${senderId}`);
    }

    async function handleIce(message) {
      const senderId = toId(message.sender_id);
      const entry = peers.get(senderId);
      const candidate = message.payload && message.payload.candidate;
      if (!entry || !candidate) return;

      if (!entry.pc.remoteDescription) {
        entry.pendingIce.push(candidate);
        return;
      }
      try {
        await entry.pc.addIceCandidate(candidate);
      } catch (err) {
        log("Falha ao adicionar ICE: " + (err.message || err));
      }
    }

    async function handleViewerReady(message) {
      if (!isOwner || !sharing) return;
      const viewerId = toId(message.sender_id);
      if (viewerId === null || viewerId === selfId) return;

      // Avoid stomping a healthy connection with a duplicate ready.
      const existing = peers.get(viewerId);
      if (
        existing &&
        (existing.pc.connectionState === "connected" ||
          existing.pc.connectionState === "connecting")
      ) {
        log(`Viewer ${viewerId} já conectado; offer ignorado.`);
        return;
      }
      await createOfferFor(viewerId);
    }

    async function attachMicrophone() {
      try {
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
          },
          video: false,
        });
        micStream.getAudioTracks().forEach((track) => {
          localStream.addTrack(track);
        });
        return true;
      } catch (err) {
        log("Microfone não disponível.");
        return false;
      }
    }

    async function startSharing({ withMicrophone = false } = {}) {
      if (!isOwner) {
        throw new Error("Apenas o proprietário pode compartilhar a tela.");
      }

      // IMPORTANT: browsers control system-audio capture. We cannot force
      // full-screen audio if the OS/browser does not expose it (common on Linux).
      try {
        localStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
          },
        });
      } catch (err) {
        localStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });
      }

      const displayAudioCount = localStream.getAudioTracks().length;
      const videoTrack = localStream.getVideoTracks()[0];
      const surface =
        (videoTrack.getSettings && videoTrack.getSettings().displaySurface) || "desconhecida";

      if (displayAudioCount === 0) {
        log(
          `Sem áudio da superfície (${surface}). ` +
            "No Chrome/Linux, áudio do sistema em tela inteira geralmente não é oferecido — use uma ABA com “Compartilhar áudio”."
        );
      }

      let usedMic = false;
      if (withMicrophone) {
        usedMic = await attachMicrophone();
      } else if (displayAudioCount === 0) {
        const wantMic = window.confirm(
          "Esta captura não trouxe áudio da tela (comum em “tela inteira” no Linux).\n\n" +
            "Para áudio do vídeo/jogo: compartilhe uma ABA do Chrome e marque “Compartilhar áudio”.\n\n" +
            "Deseja incluir o MICROFONE agora como fallback? (não captura o som do sistema)"
        );
        if (wantMic) {
          usedMic = await attachMicrophone();
        }
      }

      const audioTracks = localStream.getAudioTracks();
      audioTracks.forEach((track) => {
        track.enabled = true;
      });

      if (audioTracks.length === 0) {
        log("Transmissão seguirá sem áudio.");
      } else if (displayAudioCount > 0) {
        log(`Áudio da tela/aba capturado (${displayAudioCount} faixa(s)).`);
      } else if (usedMic) {
        log("Usando microfone (sem áudio do sistema).");
      }

      videoTrack.addEventListener("ended", () => {
        stopSharing({ notify: true });
      });

      sharing = true;
      if (onLocalStream) {
        onLocalStream(localStream, {
          hasAudio: audioTracks.length > 0,
          hasDisplayAudio: displayAudioCount > 0,
          displaySurface: surface,
          usedMicrophone: usedMic,
        });
      }

      sendSignal({
        type: "stream.started",
        payload: {
          has_audio: audioTracks.length > 0,
          has_display_audio: displayAudioCount > 0,
          display_surface: surface,
        },
      });

      return localStream;
    }

    function stopSharing({ notify = true } = {}) {
      sharing = false;
      closeAllPeers();
      stopTracks(localStream);
      stopTracks(micStream);
      localStream = null;
      micStream = null;
      if (notify) {
        sendSignal({ type: "stream.stopped", payload: {} });
      }
      if (onStreamStopped) onStreamStopped();
    }

    function requestStream() {
      if (isOwner) return;
      if (presenterId === null) {
        log("ownerId ausente; não foi possível pedir o stream.");
        return;
      }
      sendSignal({
        type: "viewer.ready",
        target_user_id: presenterId,
        payload: {},
      });
      log("Solicitando transmissão ao apresentador…");
    }

    async function handleSignal(message) {
      try {
        switch (message.type) {
          case "webrtc.offer":
            await handleOffer(message);
            break;
          case "webrtc.answer":
            await handleAnswer(message);
            break;
          case "webrtc.ice_candidate":
            await handleIce(message);
            break;
          case "viewer.ready":
            await handleViewerReady(message);
            break;
          case "stream.started":
            if (!isOwner) {
              // Small delay so presenter's send queue is ready.
              window.setTimeout(() => requestStream(), 150);
            }
            break;
          case "stream.stopped":
            if (!isOwner) {
              closeAllPeers();
              if (onStreamStopped) onStreamStopped();
            }
            break;
          case "presence.offline":
          case "participant.left":
          case "participant.removed": {
            const leavingId = toId(
              (message.user && message.user.id) || message.user_id || message.sender_id
            );
            if (leavingId !== null) closePeer(leavingId);
            break;
          }
          default:
            break;
        }
      } catch (err) {
        emitError(err);
        log("Erro WebRTC: " + (err.message || err));
      }
    }

    function destroy() {
      stopSharing({ notify: false });
    }

    return {
      startSharing,
      stopSharing,
      requestStream,
      handleSignal,
      destroy,
      isSharing: () => sharing,
    };
  }

  window.TransmissaoWebRTC = {
    createSession,
  };
})(window);
