"""
PASSO 2 — Loop de Conversa (multi-turn)
=========================================
Conceito: memória simulada via acúmulo de mensagens.

O modelo é stateless — não lembra de nada entre chamadas.
A "memória" é a lista `messages` que cresce a cada turno
e é reenviada inteira para a API em cada chamada.

Digite 'sair' para encerrar o jogo.
"""

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()

# O system prompt define o narrador para toda a sessão.
# É a única mensagem que nunca muda na lista.
SYSTEM_PROMPT = """Você é um narrador de RPG de fantasia medieval sombria.
Regras:
- Respostas curtas (3 a 5 linhas)
- Tom atmosférico e imersivo
- Sempre termine descrevendo o ambiente ou situação, deixando o jogador decidir o próximo passo
- Nunca decida ações pelo jogador
"""

# Aqui começa o histórico. O system prompt entra uma vez e fica para sempre.
messages = [
    {"role": "system", "content": SYSTEM_PROMPT}
]


def chamar_narrador(messages: list) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content


def mostrar_status(messages: list):
    # Conta apenas as mensagens user/assistant, sem o system
    turnos = (len(messages) - 1) // 2
    print(f"\n[Turno {turnos} | Mensagens no histórico: {len(messages)}]")


# ── Início da sessão ──────────────────────────────────────────────────────────

print("=" * 60)
print("  RPG NARRADO — Passo 2: Loop de Conversa")
print("  Digite 'sair' para encerrar")
print("=" * 60)

# Primeira narração: o narrador abre a cena sem input do jogador
abertura = chamar_narrador(messages + [
    {"role": "user", "content": "Descreva a cena inicial do jogo."}
])
print(f"\nNARRADOR:\n{abertura}\n")

# Adiciona a abertura ao histórico como se fosse o primeiro turno real
messages.append({"role": "user", "content": "Descreva a cena inicial do jogo."})
messages.append({"role": "assistant", "content": abertura})

# ── Loop principal ────────────────────────────────────────────────────────────

while True:
    acao = input("JOGADOR: ").strip()

    if acao.lower() == "sair":
        print("\nAté a próxima aventura!")
        break

    if not acao:
        continue

    # 1. Adiciona a ação do jogador ao histórico
    messages.append({"role": "user", "content": acao})

    # 2. Envia o histórico INTEIRO para a API
    #    (é assim que o modelo "lembra" tudo que aconteceu)
    resposta = chamar_narrador(messages)

    # 3. Adiciona a resposta do narrador ao histórico
    messages.append({"role": "assistant", "content": resposta})

    # 4. Exibe a resposta e o tamanho atual do histórico
    print(f"\nNARRADOR:\n{resposta}")
    mostrar_status(messages)
    print()