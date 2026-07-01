"""
PASSO 7 — Streaming
====================
Conceito: em vez de esperar a resposta completa para exibir tudo de uma vez,
receber e exibir o texto token por token conforme o modelo gera.

Sem streaming:  modelo processa 10 segundos → você vê tudo de uma vez
Com streaming:  você vê cada palavra aparecer enquanto o modelo gera

Por que isso importa para uma plataforma:
  - UX muito superior — parece que o narrador está "digitando"
  - O usuário não fica olhando para uma tela vazia
  - Você pode cancelar no meio se necessário
  - Permite mostrar progresso em respostas longas

A API retorna um iterador de "chunks" (pedaços de texto).
Cada chunk contém um fragmento do token gerado.
"""

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import time

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()

SYSTEM_PROMPT = """Você é um narrador de RPG de fantasia medieval sombria.
Respostas com 5 a 8 linhas, atmosféricas e detalhadas —
para que o efeito do streaming seja bem visível."""


# ── Comparação direta: sem vs. com streaming ──────────────────────────────────

def chamar_sem_streaming(messages: list) -> str:
    """Chamada normal — bloqueia até a resposta completa chegar."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content


def chamar_com_streaming(messages: list) -> str:
    """
    Chamada com streaming — exibe cada token conforme chega.
    Retorna o texto completo ao final para uso no histórico.
    """
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,          # <-- única mudança na chamada à API
    )

    texto_completo = ""

    for chunk in stream:                              # itera sobre os pedaços
        delta = chunk.choices[0].delta.content        # fragmento de texto
        if delta:
            print(delta, end="", flush=True)          # exibe sem quebra de linha
            texto_completo += delta                   # acumula para o histórico

    print()  # quebra de linha ao final
    return texto_completo


# ── Demonstração da diferença ─────────────────────────────────────────────────

messages_demo = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": "Descrevo entrar em uma floresta sombria ao anoitecer."},
]

print("=" * 60)
print("  PASSO 7 — Streaming")
print("=" * 60)

print("\n── SEM STREAMING ──────────────────────────────────────────")
print("(aguardando resposta completa...)\n")
inicio = time.time()
resposta = chamar_sem_streaming(messages_demo)
duracao = time.time() - inicio
print(resposta)
print(f"\n  [resposta chegou de uma vez após {duracao:.1f}s]")

input("\nPressione Enter para ver COM streaming...\n")

print("── COM STREAMING ──────────────────────────────────────────")
print("NARRADOR:")
inicio = time.time()
resposta = chamar_com_streaming(messages_demo)
duracao = time.time() - inicio
print(f"\n  [último token chegou em {duracao:.1f}s — mesmo tempo, UX diferente]")


# ── Loop de jogo com streaming ────────────────────────────────────────────────

input("\nPressione Enter para iniciar o jogo com streaming...\n")

print("=" * 60)
print("  RPG NARRADO — com Streaming")
print("  Digite 'sair' para encerrar")
print("=" * 60)

historico = []

# Abertura
system = [{"role": "system", "content": SYSTEM_PROMPT}]
abertura_msgs = system + [{"role": "user", "content": "Descreva a cena inicial em uma vila abandonada."}]

print("\nNARRADOR:\n")
abertura = chamar_com_streaming(abertura_msgs)

historico.append({"role": "user", "content": "Descreva a cena inicial em uma vila abandonada."})
historico.append({"role": "assistant", "content": abertura})

while True:
    acao = input("\nJOGADOR: ").strip()

    if acao.lower() == "sair":
        print("\nAté a próxima aventura!")
        break

    if not acao:
        continue

    historico.append({"role": "user", "content": acao})

    messages = system + historico
    print("\nNARRADOR:\n")

    resposta = chamar_com_streaming(messages)

    historico.append({"role": "assistant", "content": resposta})