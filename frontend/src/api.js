const BASE = "http://localhost:8000";

export const api = {
  listarSistemas: () =>
    fetch(`${BASE}/sistemas`).then((r) => r.json()),

  listarSessoes: () =>
    fetch(`${BASE}/sessoes`).then((r) => r.json()),

  criarSessao: (sistema_id) =>
    fetch(`${BASE}/sessoes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sistema_id }),
    }).then((r) => r.json()),

  onboardingTurno: (session_id, mensagem) =>
    fetch(`${BASE}/sessoes/${session_id}/onboarding`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensagem }),
    }).then((r) => r.json()),

  obterSessao: (session_id) =>
    fetch(`${BASE}/sessoes/${session_id}`).then((r) => r.json()),

  // Streaming de tokens e eventos de rolagem de dado
  // onToken(str)     → fragmento de texto da narração
  // onRolagem(obj)   → resultado de uma rolagem de dado
  // onDone()         → fim da resposta
  executarAcao: (session_id, acao, onToken, onRolagem, onDone) => {
    fetch(`${BASE}/sessoes/${session_id}/acao`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ acao }),
    }).then(async (res) => {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          if (data === "[DONE]") { onDone(); return; }
          try {
            const payload = JSON.parse(data);
            if (payload.token)   onToken(payload.token);
            if (payload.rolagem) onRolagem(payload.rolagem);
          } catch {}
        }
      }
      onDone();
    });
  },
};
