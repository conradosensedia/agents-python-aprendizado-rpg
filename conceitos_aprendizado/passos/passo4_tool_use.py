"""
PASSO 4 — Tool Use (Uso de Ferramentas)
=========================================
Conceito: o modelo pode chamar funções Python de forma autônoma.

O fluxo de uma chamada com tools:
  1. Você define as ferramentas disponíveis (schema JSON)
  2. Envia mensagens + ferramentas para a API
  3. O modelo decide se precisa chamar uma ferramenta
  4. Se sim: devolve tool_calls (nome + argumentos) em vez de texto
  5. Você executa a função e adiciona o resultado às mensagens
  6. Chama a API novamente com o resultado
  7. O modelo gera a resposta final usando o resultado

Este ciclo (passos 3-6) pode se repetir várias vezes antes da
resposta final — isso é o loop agêntico.
"""

import json
import random
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()


# ── Estado do jogo ────────────────────────────────────────────────────────────

personagem = {
    "nome": "Aldric",
    "classe": "Guerreiro",
    "hp": 20,
    "hp_max": 20,
    "forca": 14,
    "destreza": 10,
    "inventario": ["espada enferrujada", "tocha", "pão duro"],
    "ouro": 5,
}

mundo = {
    "localizacao": "Entrada da Vila de Cinzas",
    "hora": "noite",
    "clima": "névoa densa",
}


# ── Ferramentas (funções reais em Python) ─────────────────────────────────────
# Estas são as funções que o MODELO pode solicitar que sejam executadas.
# O modelo não as executa — ele pede, você executa e devolve o resultado.

def rolar_dado(lados: int) -> dict:
    """Rola um dado de N lados e retorna o resultado."""
    resultado = random.randint(1, lados)
    print(f"  🎲 [TOOL] rolar_dado({lados}) → {resultado}")
    return {"resultado": resultado, "lados": lados}


def verificar_habilidade(atributo: str, dificuldade: int) -> dict:
    """Verifica se o personagem passa em um teste de habilidade."""
    valor_atributo = personagem.get(atributo, 10)
    modificador = (valor_atributo - 10) // 2  # cálculo D&D clássico
    rolagem = random.randint(1, 20)
    total = rolagem + modificador
    sucesso = total >= dificuldade

    print(f"  🎲 [TOOL] verificar_habilidade({atributo}, dificuldade={dificuldade})")
    print(f"       rolagem={rolagem}, modificador={modificador:+}, total={total} → {'SUCESSO' if sucesso else 'FALHA'}")

    return {
        "atributo": atributo,
        "rolagem": rolagem,
        "modificador": modificador,
        "total": total,
        "dificuldade": dificuldade,
        "sucesso": sucesso,
    }


def atualizar_hp(quantidade: int) -> dict:
    """Aplica dano (negativo) ou cura (positivo) ao personagem."""
    hp_antes = personagem["hp"]
    personagem["hp"] = max(0, min(personagem["hp_max"], personagem["hp"] + quantidade))
    hp_depois = personagem["hp"]

    acao = "curou" if quantidade > 0 else "sofreu dano"
    print(f"  ❤️  [TOOL] atualizar_hp({quantidade:+}) → {hp_antes} → {hp_depois}")

    return {
        "hp_antes": hp_antes,
        "hp_depois": hp_depois,
        "quantidade": quantidade,
        "vivo": personagem["hp"] > 0,
    }


def adicionar_item(item: str) -> dict:
    """Adiciona um item ao inventário do personagem."""
    personagem["inventario"].append(item)
    print(f"  🎒 [TOOL] adicionar_item('{item}')")
    return {"item": item, "inventario": personagem["inventario"]}


# ── Mapa de nome → função ─────────────────────────────────────────────────────
# Usado para despachar a chamada quando o modelo pede uma ferramenta.

FERRAMENTAS_DISPONIVEIS = {
    "rolar_dado": rolar_dado,
    "verificar_habilidade": verificar_habilidade,
    "atualizar_hp": atualizar_hp,
    "adicionar_item": adicionar_item,
}


# ── Schema das ferramentas (o que a API recebe) ───────────────────────────────
# O modelo não vê o código Python — ele vê este schema JSON.
# É a "documentação" que ensina ao modelo quando e como chamar cada função.

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "rolar_dado",
            "description": "Rola um dado de N lados. Use para resolver ações com elemento de sorte ou risco.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lados": {
                        "type": "integer",
                        "description": "Número de lados do dado (ex: 6, 20)",
                    }
                },
                "required": ["lados"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verificar_habilidade",
            "description": "Testa se o personagem consegue realizar uma ação baseada em um atributo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "atributo": {
                        "type": "string",
                        "description": "Atributo a testar: 'forca' ou 'destreza'",
                        "enum": ["forca", "destreza"],
                    },
                    "dificuldade": {
                        "type": "integer",
                        "description": "Valor mínimo necessário para passar no teste (1-30)",
                    },
                },
                "required": ["atributo", "dificuldade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "atualizar_hp",
            "description": "Aplica dano ou cura ao personagem. Use valor negativo para dano, positivo para cura.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quantidade": {
                        "type": "integer",
                        "description": "Pontos de HP. Negativo = dano (ex: -5), positivo = cura (ex: +3)",
                    }
                },
                "required": ["quantidade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adicionar_item",
            "description": "Adiciona um item ao inventário do personagem quando ele encontra ou pega algo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "Nome do item a adicionar",
                    }
                },
                "required": ["item"],
            },
        },
    },
]


# ── System prompt ─────────────────────────────────────────────────────────────

def montar_system_prompt(personagem: dict, mundo: dict) -> str:
    inventario = ", ".join(personagem["inventario"]) if personagem["inventario"] else "nenhum"
    return f"""Você é um narrador de RPG de fantasia medieval sombria com acesso a ferramentas.

## ESTADO ATUAL DO JOGO
Personagem : {personagem['nome']} ({personagem['classe']})
HP         : {personagem['hp']}/{personagem['hp_max']}
Força      : {personagem['forca']} | Destreza: {personagem['destreza']}
Inventário : {inventario}
Ouro       : {personagem['ouro']} moedas
Localização: {mundo['localizacao']} | {mundo['hora']} | {mundo['clima']}

## QUANDO USAR FERRAMENTAS
- Ação arriscada ou com sorte envolvida → rolar_dado ou verificar_habilidade
- Personagem leva dano ou é curado → atualizar_hp
- Personagem encontra ou pega um item → adicionar_item
- Narração simples sem consequência mecânica → responda diretamente, sem tools

## REGRAS DE NARRAÇÃO
- Respostas curtas (3 a 5 linhas)
- Narre o resultado APÓS receber o retorno das ferramentas
- Nunca decida ações pelo jogador
"""


# ── Loop agêntico ─────────────────────────────────────────────────────────────
# Esta é a função central do passo 4.
# Ela chama a API repetidamente até o modelo dar uma resposta final de texto
# (sem mais tool_calls). A cada iteração, executa as funções pedidas.

def chamar_narrador(messages: list) -> str:
    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",  # o modelo decide se usa ou não uma ferramenta
        )

        msg = response.choices[0].message

        # Caso 1: o modelo quer chamar ferramentas
        if msg.tool_calls:
            # Adiciona a mensagem do modelo (com os tool_calls) ao histórico
            messages.append(msg)

            # Executa cada ferramenta pedida e devolve o resultado
            for tool_call in msg.tool_calls:
                nome = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                funcao = FERRAMENTAS_DISPONIVEIS[nome]
                resultado = funcao(**args)

                # O resultado entra no histórico como role "tool"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(resultado),
                })

            # Volta ao início do while: chama a API de novo com os resultados
            continue

        # Caso 2: o modelo deu uma resposta final de texto — sai do loop
        return msg.content


# ── Interface do jogo ─────────────────────────────────────────────────────────

def mostrar_status(personagem: dict, mundo: dict):
    barra = "█" * personagem["hp"] + "░" * (personagem["hp_max"] - personagem["hp"])
    print(f"\n  [{personagem['nome']} | HP: {barra} {personagem['hp']}/{personagem['hp_max']} | {mundo['localizacao']}]")


print("=" * 60)
print("  RPG NARRADO — Passo 4: Tool Use")
print("  Observe as linhas [TOOL] para ver as ferramentas sendo chamadas")
print("  Digite 'sair' para encerrar")
print("=" * 60)

historico = []

# Abertura
system = montar_system_prompt(personagem, mundo)
abertura = chamar_narrador([
    {"role": "system", "content": system},
    {"role": "user", "content": "Descreva a cena inicial."},
])
print(f"\nNARRADOR:\n{abertura}")
mostrar_status(personagem, mundo)
print()

historico.append({"role": "user", "content": "Descreva a cena inicial."})
historico.append({"role": "assistant", "content": abertura})

while True:
    acao = input("\nJOGADOR: ").strip()

    if acao.lower() == "sair":
        print("\nAté a próxima aventura!")
        break

    if not acao:
        continue

    system = montar_system_prompt(personagem, mundo)
    messages = [{"role": "system", "content": system}] + historico + [
        {"role": "user", "content": acao}
    ]

    print()
    resposta = chamar_narrador(messages)

    historico.append({"role": "user", "content": acao})
    historico.append({"role": "assistant", "content": resposta})

    print(f"\nNARRADOR:\n{resposta}")
    mostrar_status(personagem, mundo)
