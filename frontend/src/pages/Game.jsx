import { useState, useEffect, useRef } from "react";
import { api } from "../api";

function CartaRolagem({ rolagem }) {
  const { notacao, modificador, motivo, resultados_individuais, total, critico, falha_critica } = rolagem;
  const classe = critico ? "rolagem critico" : falha_critica ? "rolagem falha-critica" : "rolagem";

  return (
    <div className={classe}>
      <span className="rolagem-dado">🎲 {notacao}</span>
      <div className="rolagem-corpo">
        <span className="rolagem-motivo">{motivo}</span>
        <div className="rolagem-numeros">
          <span className="rolagem-individuais">
            [{resultados_individuais.join(" + ")}]
          </span>
          {modificador !== 0 && (
            <span className="rolagem-mod">{modificador > 0 ? `+${modificador}` : modificador}</span>
          )}
          <span className="rolagem-total">{total}</span>
        </div>
        {critico      && <span className="rolagem-badge">CRÍTICO!</span>}
        {falha_critica && <span className="rolagem-badge falha">FALHA CRÍTICA</span>}
      </div>
    </div>
  );
}

export default function Game({ sessionId, onVoltar }) {
  const [mensagens, setMensagens] = useState([]);
  const [personagem, setPersonagem] = useState(null);
  const [input, setInput] = useState("");
  const [narrando, setNarrando] = useState(false);
  const fimRef = useRef(null);
  const iniciado = useRef(false);

  useEffect(() => {
    api.obterSessao(sessionId).then(({ sessao, personagem }) => {
      setPersonagem(personagem);
      const hist = sessao.historico_chat || [];
      if (hist.length === 0 && !iniciado.current) {
        iniciado.current = true;
        narrar("Descreva a cena inicial da aventura, apresentando o mundo ao personagem.");
      } else {
        setMensagens(hist.map((m) => ({ role: m.role, content: m.content })));
      }
    });
  }, []);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens]);

  function narrar(acao) {
    if (narrando) return;
    setNarrando(true);

    const ehAbertura = acao === "Descreva a cena inicial da aventura, apresentando o mundo ao personagem.";
    if (!ehAbertura) {
      setMensagens((m) => [...m, { role: "user", content: acao }]);
    }

    // Placeholder para a resposta do narrador (texto que vai crescendo)
    setMensagens((m) => [...m, { role: "assistant", content: "" }]);

    let resposta = "";

    api.executarAcao(
      sessionId,
      acao,
      // onToken — atualiza o último item (a mensagem do narrador)
      (token) => {
        resposta += token;
        setMensagens((m) => {
          const novas = [...m];
          novas[novas.length - 1] = { role: "assistant", content: resposta };
          return novas;
        });
      },
      // onRolagem — insere um card de dado ANTES da última mensagem (o narrador ainda está escrevendo)
      (rolagem) => {
        setMensagens((m) => {
          const novas = [...m];
          const ultima = novas.pop(); // remove o placeholder do narrador
          return [...novas, { role: "rolagem", rolagem }, ultima];
        });
      },
      // onDone
      () => {
        setNarrando(false);
        api.obterSessao(sessionId).then(({ personagem }) => setPersonagem(personagem));
      }
    );
  }

  function enviar() {
    const acao = input.trim();
    if (!acao || narrando) return;
    setInput("");
    narrar(acao);
  }

  return (
    <div className="game">
      <aside className="ficha">
        {personagem && (
          <>
            <h3>{personagem.nome}</h3>
            <p className="ficha-classe">{personagem.raca} · {personagem.classe}</p>
            <div className="ficha-hp">
              <span>HP</span>
              <div className="hp-barra">
                <div
                  className="hp-preenchido"
                  style={{ width: `${(personagem.hp_atual / personagem.hp_maximo) * 100}%` }}
                />
              </div>
              <span>{personagem.hp_atual}/{personagem.hp_maximo}</span>
            </div>
            <div className="ficha-atributos">
              {Object.entries(personagem.atributos || {}).map(([k, v]) => {
                const mod = Math.floor((v - 10) / 2);
                return (
                  <div key={k} className="atributo">
                    <span className="atributo-nome">{k.slice(0, 3)}</span>
                    <span className="atributo-valor">{v}</span>
                    <span className="atributo-mod">{mod >= 0 ? `+${mod}` : mod}</span>
                  </div>
                );
              })}
            </div>
            <div className="ficha-inventario">
              <h4>Inventário</h4>
              {(personagem.inventario || []).length === 0
                ? <p className="vazio">Vazio</p>
                : personagem.inventario.map((item, i) => <p key={i}>· {item}</p>)
              }
            </div>
            <p className="ficha-ouro">💰 {personagem.ouro} po</p>
          </>
        )}
        <button className="btn-voltar" onClick={onVoltar}>← Início</button>
      </aside>

      <main className="narrativa">
        <div className="chat-container">
          {mensagens.map((m, i) => {
            if (m.role === "rolagem") {
              return <CartaRolagem key={i} rolagem={m.rolagem} />;
            }
            if (m.role === "assistant") {
              return (
                <div key={i} className="mensagem assistant">
                  <p className="narrativa-texto">
                    {m.content}
                    {narrando && i === mensagens.length - 1 && <span className="cursor">▋</span>}
                  </p>
                </div>
              );
            }
            return (
              <div key={i} className="mensagem user">
                <p className="acao-texto">▶ {m.content}</p>
              </div>
            );
          })}
          <div ref={fimRef} />
        </div>

        <div className="chat-input">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && enviar()}
            placeholder="O que você faz?"
            disabled={narrando}
          />
          <button onClick={enviar} disabled={narrando || !input.trim()}>
            {narrando ? "..." : "Agir"}
          </button>
        </div>
      </main>
    </div>
  );
}
