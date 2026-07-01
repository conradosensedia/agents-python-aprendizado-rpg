"""
PASSO 3 — System Prompt Dinâmico
==================================
Conceito: o estado do jogo é injetado no system prompt a cada turno.

O modelo não "vê" o mundo — ele só vê texto. Para que o narrador
saiba que o personagem tem 10 HP ou está em uma floresta, você
precisa colocar essa informação explicitamente no prompt.

A separação central deste passo:
  - Estado do jogo  → dicionários Python (a verdade)
  - System prompt   → representação textual do estado (o que o modelo vê)
"""

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()


# ── Estado do jogo ────────────────────────────────────────────────────────────
# Esta é a "fonte da verdade". O modelo nunca acessa isso diretamente —
# ele só vê a representação textual que montamos abaixo.

personagem = {
    "nome": "Aldric",
    "classe": "Guerreiro",
    "hp": 20,
    "hp_max": 20,
    "inventario": ["espada enferrujada", "tocha", "pão duro"],
    "ouro": 5,
}

mundo = {
    "localizacao": "Entrada da Vila de Cinzas",
    "hora": "noite",
    "clima": "névoa densa",
}


# ── Construtor do system prompt ───────────────────────────────────────────────
# Esta função é chamada a cada turno, sempre com os valores mais recentes.
# É aqui que o estado Python vira texto para o modelo.

def montar_system_prompt(personagem: dict, mundo: dict) -> str:
    inventario = ", ".join(personagem["inventario"]) if personagem["inventario"] else "nenhum"

    return f"""Você é um narrador de RPG de fantasia medieval sombria.

## ESTADO ATUAL DO JOGO
Personagem : {personagem['nome']} ({personagem['classe']})
HP         : {personagem['hp']}/{personagem['hp_max']}
Inventário : {inventario}
Ouro       : {personagem['ouro']} moedas

Localização: {mundo['localizacao']}
Hora       : {mundo['hora']}
Clima      : {mundo['clima']}

## REGRAS DE NARRAÇÃO
- Respostas curtas (3 a 5 linhas)
- Use os dados acima para tornar a narrativa coerente
- Se o personagem estiver com pouco HP, reflita isso no tom (cansaço, ferimentos)
- Nunca decida ações pelo jogador
- Termine sempre descrevendo a situação atual, não uma pergunta direta
"""


def chamar_narrador(messages: list) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content


def mostrar_status(personagem: dict, mundo: dict):
    barra_hp = "█" * personagem["hp"] + "░" * (personagem["hp_max"] - personagem["hp"])
    print(f"\n  [{personagem['nome']} | HP: {barra_hp} {personagem['hp']}/{personagem['hp_max']} | {mundo['localizacao']}]")


# ── Início da sessão ──────────────────────────────────────────────────────────

print("=" * 60)
print("  RPG NARRADO — Passo 3: System Prompt Dinâmico")
print("  Digite 'sair' para encerrar")
print("  Digite 'dano X' para simular receber X de dano (ex: dano 5)")
print("  Digite 'mover LUGAR' para mudar de localização (ex: mover Taverna)")
print("=" * 60)

# Histórico começa vazio — o system será montado dinamicamente a cada chamada
historico = []

# Cena de abertura
system_inicial = montar_system_prompt(personagem, mundo)
abertura = chamar_narrador([
    {"role": "system", "content": system_inicial},
    {"role": "user", "content": "Descreva a cena inicial."},
])
print(f"\nNARRADOR:\n{abertura}")
mostrar_status(personagem, mundo)
print()

historico.append({"role": "user", "content": "Descreva a cena inicial."})
historico.append({"role": "assistant", "content": abertura})


# ── Loop principal ────────────────────────────────────────────────────────────

while True:
    acao = input("\nJOGADOR: ").strip()

    if acao.lower() == "sair":
        print("\nAté a próxima aventura!")
        break

    if not acao:
        continue

    # Comandos de simulação para ver o system prompt mudando
    if acao.lower().startswith("dano "):
        dano = int(acao.split()[1])
        personagem["hp"] = max(0, personagem["hp"] - dano)
        print(f"  → Você sofreu {dano} de dano. HP: {personagem['hp']}/{personagem['hp_max']}")
        continue

    if acao.lower().startswith("mover "):
        lugar = acao[6:].strip()
        mundo["localizacao"] = lugar
        print(f"  → Localização alterada para: {lugar}")
        continue

    # A cada turno, o system prompt é RECONSTRUÍDO com o estado atual.
    # O historico de user/assistant permanece o mesmo — só o system muda.
    system_atual = montar_system_prompt(personagem, mundo)

    messages = [{"role": "system", "content": system_atual}] + historico
    messages.append({"role": "user", "content": acao})

    resposta = chamar_narrador(messages)

    historico.append({"role": "user", "content": acao})
    historico.append({"role": "assistant", "content": resposta})

    print(f"\nNARRADOR:\n{resposta}")
    mostrar_status(personagem, mundo)