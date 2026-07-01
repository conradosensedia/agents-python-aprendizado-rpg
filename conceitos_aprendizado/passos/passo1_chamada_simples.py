"""
PASSO 1 — Uma única chamada à API
==================================
Conceito: toda interação com um LLM é uma lista de mensagens.
Cada mensagem tem um 'role' (quem fala) e um 'content' (o que diz).

Roles possíveis:
  - system:    instrução permanente que define o comportamento do modelo
  - user:      o que o jogador digitou
  - assistant: o que o modelo respondeu (usado para histórico)
"""

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Procura o .env na mesma pasta do script (passos/)
load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()  # agora lê OPENAI_API_KEY do .env

# Esta é a estrutura fundamental de qualquer chamada:
# uma lista de mensagens em ordem cronológica.
messages = [
    {
        "role": "system",
        "content": (
            "Você é um narrador de RPG de fantasia medieval. "
            "Suas respostas são curtas, atmosféricas e terminam "
            "sempre com uma pergunta implícita ao jogador."
        ),
    },
    {
        "role": "user",
        "content": "Eu entro na taverna.",
    },
]

print("Enviando para a API...\n")

response = client.chat.completions.create(
    model="gpt-4o-mini",  # modelo mais barato para aprendizado
    messages=messages,
)

# A resposta vem dentro de response.choices[0].message
narrator_reply = response.choices[0].message.content

print("=== NARRADOR ===")
print(narrator_reply)
print()

# Vamos inspecionar o que a API devolveu além do texto:
print("=== METADADOS DA RESPOSTA ===")
print(f"Modelo usado:       {response.model}")
print(f"Tokens de entrada:  {response.usage.prompt_tokens}")
print(f"Tokens de saída:    {response.usage.completion_tokens}")
print(f"Total de tokens:    {response.usage.total_tokens}")