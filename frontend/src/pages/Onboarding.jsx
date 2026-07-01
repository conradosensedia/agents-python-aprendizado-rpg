import { useState, useEffect, useRef } from "react";
import { api } from "../api";

export default function Onboarding({ sessionId, onConcluido }) {
  const [mensagens, setMensagens] = useState([]);
  const [input, setInput] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [personagem, setPersonagem] = useState(null);
  const fimRef = useRef(null);
  const iniciado = useRef(false);

  useEffect(() => {
    if (iniciado.current) return;
    iniciado.current = true;
    iniciarOnboarding();
  }, []);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens]);

  async function iniciarOnboarding() {
    setCarregando(true);
    const resultado = await api.onboardingTurno(sessionId, "__inicio__");
    if (resultado.tipo === "mensagem") {
      setMensagens([{ role: "assistant", content: resultado.conteudo }]);
    }
    setCarregando(false);
  }

  async function enviar(texto) {
    const msg = texto || input.trim();
    if (!msg || carregando) return;
    setInput("");
    setCarregando(true);

    setMensagens((m) => [...m, { role: "user", content: msg }]);

    const resultado = await api.onboardingTurno(sessionId, msg);

    if (resultado.tipo === "concluido") {
      setPersonagem(resultado.personagem);
      setMensagens((m) => [
        ...m,
        { role: "assistant", content: "✅ Personagem criado! Sua aventura está prestes a começar..." },
      ]);
      setTimeout(onConcluido, 2000);
    } else {
      setMensagens((m) => [...m, { role: "assistant", content: resultado.conteudo }]);
    }
    setCarregando(false);
  }

  return (
    <div className="onboarding">
      <header className="onboarding-header">
        <h2>Criação de Personagem</h2>
        <p>Responda ao agente para montar sua ficha</p>
      </header>

      <div className="chat-container">
        {mensagens.map((m, i) => (
          <div key={i} className={`mensagem ${m.role}`}>
            <span className="mensagem-role">{m.role === "user" ? "Você" : "Agente"}</span>
            <p>{m.content}</p>
          </div>
        ))}
        {carregando && (
          <div className="mensagem assistant">
            <span className="mensagem-role">Agente</span>
            <p className="digitando">▋</p>
          </div>
        )}
        <div ref={fimRef} />
      </div>

      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && enviar()}
          placeholder="Responda aqui..."
          disabled={carregando || !!personagem}
        />
        <button onClick={() => enviar()} disabled={carregando || !input.trim() || !!personagem}>
          Enviar
        </button>
      </div>
    </div>
  );
}
