import { useEffect, useState } from "react";
import { api } from "../api";

export default function Home({ onIniciar, onContinuar }) {
  const [sistemas, setSistemas] = useState([]);
  const [sessoes, setSessoes] = useState([]);
  const [sistemaSelecionado, setSistemaSelecionado] = useState(null);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    api.listarSistemas().then(setSistemas);
    api.listarSessoes().then(setSessoes);
  }, []);

  async function iniciarAventura() {
    if (!sistemaSelecionado) return;
    setCarregando(true);
    const { session_id } = await api.criarSessao(sistemaSelecionado);
    onIniciar(session_id);
  }

  return (
    <div className="home">
      <header className="home-header">
        <h1>⚔️ RPG Narrado</h1>
        <p>Uma aventura narrada por inteligência artificial</p>
      </header>

      {sessoes.length > 0 && (
        <section className="secao">
          <h2>Aventuras em andamento</h2>
          <div className="sessoes-lista">
            {sessoes.map((s) => (
              <div key={s._id} className="sessao-card" onClick={() => onContinuar(s._id)}>
                <div className="sessao-sistema">{s.sistema_nome}</div>
                <div className="sessao-info">Turno {s.turno} · {s.localizacao}</div>
                <div className="sessao-data">
                  {new Date(s.atualizado_em).toLocaleDateString("pt-BR")}
                </div>
                <button className="btn-continuar">Continuar →</button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="secao">
        <h2>Nova aventura</h2>
        <p className="secao-desc">Escolha o sistema de RPG</p>
        <div className="sistemas-lista">
          {sistemas.map((s) => (
            <div
              key={s.id}
              className={`sistema-card ${sistemaSelecionado === s.id ? "selecionado" : ""}`}
              onClick={() => setSistemaSelecionado(s.id)}
            >
              <span className="sistema-imagem">{s.imagem}</span>
              <h3>{s.nome}</h3>
              <p>{s.descricao}</p>
            </div>
          ))}
        </div>
        <button
          className="btn-iniciar"
          disabled={!sistemaSelecionado || carregando}
          onClick={iniciarAventura}
        >
          {carregando ? "Iniciando..." : "Iniciar Aventura"}
        </button>
      </section>
    </div>
  );
}
