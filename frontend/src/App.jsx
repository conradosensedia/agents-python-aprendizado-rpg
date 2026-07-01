import { useState } from "react";
import Home from "./pages/Home";
import Onboarding from "./pages/Onboarding";
import Game from "./pages/Game";
import "./App.css";

export default function App() {
  const [tela, setTela] = useState("home");
  const [sessionId, setSessionId] = useState(null);

  const irPara = (t, sid = null) => {
    setTela(t);
    if (sid) setSessionId(sid);
  };

  return (
    <div className="app">
      {tela === "home" && (
        <Home
          onIniciar={(sid) => irPara("onboarding", sid)}
          onContinuar={(sid) => irPara("game", sid)}
        />
      )}
      {tela === "onboarding" && (
        <Onboarding sessionId={sessionId} onConcluido={() => irPara("game")} />
      )}
      {tela === "game" && (
        <Game sessionId={sessionId} onVoltar={() => irPara("home")} />
      )}
    </div>
  );
}
