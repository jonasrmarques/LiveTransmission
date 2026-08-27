/**
 * WebSocket client for room real-time events (/ws/transmissao/sala/<uuid>/).
 */
(function (window) {
  "use strict";

  function wsUrl(roomId) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/ws/transmissao/sala/${roomId}/`;
  }

  function connectRoomSocket(roomId, callbacks) {
    let socket = null;
    let closedByUser = false;
    let reconnectTimer = null;

    function clearReconnect() {
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    }

    function connect() {
      socket = new WebSocket(wsUrl(roomId));

      socket.addEventListener("open", () => {
        if (callbacks.onOpen) callbacks.onOpen();
      });

      socket.addEventListener("message", (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch (_) {
          return;
        }
        if (callbacks.onMessage) callbacks.onMessage(data);
      });

      socket.addEventListener("close", () => {
        if (callbacks.onClose) callbacks.onClose(closedByUser);
        if (!closedByUser) {
          reconnectTimer = window.setTimeout(connect, 2000);
        }
      });

      socket.addEventListener("error", () => {
        if (callbacks.onError) callbacks.onError();
      });
    }

    connect();

    return {
      send(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify(payload));
        }
      },
      close() {
        closedByUser = true;
        clearReconnect();
        if (socket) socket.close();
      },
    };
  }

  window.TransmissaoWebSocket = {
    connectRoomSocket,
  };
})(window);
