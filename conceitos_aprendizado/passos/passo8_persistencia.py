"""
PASSO 8 — Persistência de Estado
==================================
Conceito: salvar e carregar o estado completo do jogo entre sessões.

Sem persistência, cada vez que o programa fecha tudo se perde:
ficha do personagem, inventário, localização, histórico da conversa.

O que precisa persistir:
  - Estado do personagem (hp, inventário, atributos, ouro)
  - Estado do mundo (localização, hora, eventos ocorridos)
  - Histórico do chat (para o narrador lembrar a sessão atual)
  - Metadados da sessão (quando foi, quantos turnos)

Formato escolhido: JSON — legível, editável, sem dependências.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

client  = OpenAI()
SAVES_PATH = Path(__file__).parent.parent / "storage" / "saves"
SAVES_PATH.mkdir(parents=True, exist_ok=True)


# ── Estrutura do save ─────────────────────────────────────────────────────────

def novo_jogo(nome_personagem: str) -> dict:
    """Cria um estado inicial para um novo jogo."""
    return {
        "meta": {
            "id": str(uuid.uuid4()),
            "criado_em": datetime.now().isoformat(),
            "salvo_em": None,
            "turnos": 0,
        },
        "personagem": {
            "nome": nome_personagem,
            "classe": "Guerreiro",
            "hp": 20,
            "hp_max": 20,
            "forca": 14,
            "destreza": 10,
            "inventario": ["espada enferrujada", "tocha", "pão duro"],
            "ouro": 5,
        },
        "mundo": {
            "localizacao": "Vila de Cinzas",
            "hora": "noite",
            "clima": "névoa densa",
            "eventos": [],        # eventos importantes que ocorreram
        },
        "historico_chat": [],     # mensagens user/assistant da sessão
    }


# ── Salvar e carregar ─────────────────────────────────────────────────────────

def salvar(estado: dict) -> Path:
    """Serializa o estado completo para JSON e grava em disco."""
    estado["meta"]["salvo_em"] = datetime.now().isoformat()

    # Nome do arquivo usa o id único do jogo
    arquivo = SAVES_PATH / f"{estado['meta']['id']}.json"
    arquivo.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return arquivo


def carregar(arquivo: Path) -> dict:
    """Lê um arquivo de save e retorna o estado."""
    return json.loads(arquivo.read_text(encoding="utf-8"))


def listar_saves() -> list[Path]:
    """Retorna todos os saves disponíveis, do mais recente ao mais antigo."""
    saves = list(SAVES_PATH.glob("*.json"))
    saves.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return saves


# ── Tela de seleção de save ───────────────────────────────────────────────────

def tela_inicial() -> dict:
    """Permite ao jogador criar um jogo novo ou continuar um salvo."""
    saves = listar_saves()

    print("\n" + "=" * 60)
    print("  RPG NARRADO — Passo 8: Persistência de Estado")
    print("=" * 60)

    if not saves:
        print("\n  Nenhum save encontrado. Iniciando novo jogo.\n")
        nome = input("  Nome do seu personagem: ").strip() or "Aldric"
        return novo_jogo(nome)

    print("\n  Saves disponíveis:")
    print("  [0] Novo jogo")

    estados_resumo = []
    for i, arquivo in enumerate(saves[:5], 1):
        estado = carregar(arquivo)
        p = estado["personagem"]
        m = estado["mundo"]
        meta = estado["meta"]
        salvo = meta["salvo_em"][:16].replace("T", " ") if meta["salvo_em"] else "?"
        print(f"  [{i}] {p['nome']} ({p['classe']}) — "
              f"HP {p['hp']}/{p['hp_max']} — "
              f"{m['localizacao']} — "
              f"{meta['turnos']} turnos — "
              f"salvo {salvo}")
        estados_resumo.append((arquivo, estado))

    escolha = input("\n  Escolha [0-{}]: ".format(len(estados_resumo))).strip()

    if escolha == "0" or not escolha.isdigit():
        nome = input("  Nome do seu personagem: ").strip() or "Aldric"
        return novo_jogo(nome)

    idx = int(escolha) - 1
    if 0 <= idx < len(estados_resumo):
        _, estado = estados_resumo[idx]
        print(f"\n  Save carregado: {estado['personagem']['nome']} — {estado['mundo']['localizacao']}")
        return estado

    nome = input("  Opção inválida. Nome do personagem: ").strip() or "Aldric"
    return novo_jogo(nome)


# ── Narrador com streaming ────────────────────────────────────────────────────

def montar_system_prompt(estado: dict) -> str:
    p = estado["personagem"]
    m = estado["mundo"]
    inventario = ", ".join(p["inventario"]) or "nenhum"
    eventos = "\n".join(f"- {e}" for e in m["eventos"][-5:]) or "nenhum"

    return f"""Você é um narrador de RPG de fantasia medieval sombria.

## ESTADO ATUAL
Personagem : {p['nome']} ({p['classe']})
HP         : {p['hp']}/{p['hp_max']}
Força      : {p['forca']} | Destreza: {p['destreza']}
Inventário : {inventario}
Ouro       : {p['ouro']} moedas

Localização: {m['localizacao']}
Hora       : {m['hora']} | Clima: {m['clima']}

Eventos anteriores relevantes:
{eventos}

## REGRAS
- Respostas curtas (3 a 5 linhas)
- Seja coerente com os eventos anteriores listados acima
- Nunca decida ações pelo jogador
"""


def chamar_narrador_stream(messages: list) -> str:
    """Chama a API com streaming e retorna o texto completo acumulado."""
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
    )
    texto = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            texto += delta
    print()
    return texto


def registrar_evento(estado: dict, evento: str):
    """Adiciona um evento importante à lista do mundo (memória leve)."""
    estado["mundo"]["eventos"].append(evento)
    if len(estado["mundo"]["eventos"]) > 20:
        estado["mundo"]["eventos"].pop(0)  # mantém só os 20 mais recentes


# ── Loop principal ────────────────────────────────────────────────────────────

estado = tela_inicial()

print("\n" + "=" * 60)
print(f"  Jogando como {estado['personagem']['nome']}")
print("  Comandos: 'salvar', 'status', 'sair'")
print("=" * 60 + "\n")

# Se é novo jogo, gera a abertura. Se é save, retoma do histórico.
if not estado["historico_chat"]:
    system = montar_system_prompt(estado)
    print("NARRADOR:\n")
    abertura = chamar_narrador_stream([
        {"role": "system", "content": system},
        {"role": "user", "content": "Descreva a cena inicial."},
    ])
    estado["historico_chat"].append({"role": "user", "content": "Descreva a cena inicial."})
    estado["historico_chat"].append({"role": "assistant", "content": abertura})
else:
    print("NARRADOR:\n")
    retomada = chamar_narrador_stream([
        {"role": "system", "content": montar_system_prompt(estado)},
        {"role": "user", "content": "Resuma brevemente onde estávamos e o que acabou de acontecer."},
    ])
    print()

while True:
    p = estado["personagem"]
    m = estado["mundo"]
    print(f"  [{p['nome']} | HP {p['hp']}/{p['hp_max']} | {m['localizacao']} | turno {estado['meta']['turnos']}]")

    acao = input("\nJOGADOR: ").strip()

    if not acao:
        continue

    if acao.lower() == "sair":
        arquivo = salvar(estado)
        print(f"\n  Jogo salvo em: {arquivo.name}")
        print("  Até a próxima aventura!")
        break

    if acao.lower() == "salvar":
        arquivo = salvar(estado)
        print(f"\n  Salvo em: {arquivo.name}\n")
        continue

    if acao.lower() == "status":
        print(f"\n  Nome      : {p['nome']} ({p['classe']})")
        print(f"  HP        : {p['hp']}/{p['hp_max']}")
        print(f"  Inventário: {', '.join(p['inventario'])}")
        print(f"  Ouro      : {p['ouro']}")
        print(f"  Local     : {m['localizacao']}")
        print(f"  Eventos   : {len(m['eventos'])} registrados\n")
        continue

    estado["meta"]["turnos"] += 1

    system = montar_system_prompt(estado)
    messages = (
        [{"role": "system", "content": system}]
        + estado["historico_chat"][-20:]        # últimas 10 trocas para não estourar contexto
        + [{"role": "user", "content": acao}]
    )

    print("\nNARRADOR:\n")
    resposta = chamar_narrador_stream(messages)

    estado["historico_chat"].append({"role": "user", "content": acao})
    estado["historico_chat"].append({"role": "assistant", "content": resposta})

    # Salva automaticamente a cada 5 turnos
    if estado["meta"]["turnos"] % 5 == 0:
        salvar(estado)
        print(f"\n  [autosave — turno {estado['meta']['turnos']}]")