"""
Agente Narrador — conduz a sessão de jogo com streaming e tool use.
"""

import json
import random
import datetime
from typing import AsyncGenerator
from openai import AsyncOpenAI
from database.mongo import get_db

client = AsyncOpenAI()

TOOL_ROLAR_DADO = {
    "type": "function",
    "function": {
        "name": "rolar_dado",
        "description": (
            "Rola dados para resolver testes, ataques, dano ou qualquer ação com aleatoriedade. "
            "Use notação padrão de D&D: 1d20 para testes e ataques, 1d6/1d8/etc para dano. "
            "Sempre especifique o motivo da rolagem."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "notacao": {
                    "type": "string",
                    "description": "Notação de dados: '1d20', '2d6', '1d8', etc.",
                },
                "modificador": {
                    "type": "integer",
                    "description": "Bônus ou penalidade a somar ao resultado (pode ser negativo).",
                },
                "motivo": {
                    "type": "string",
                    "description": "Por que este dado está sendo rolado. Ex: 'Teste de Força (CD 15)', 'Dano da espada'.",
                },
            },
            "required": ["notacao", "modificador", "motivo"],
        },
    },
}


def executar_rolar_dado(notacao: str, modificador: int, motivo: str) -> dict:
    """Interpreta a notação XdY, rola os dados e retorna o resultado completo."""
    partes = notacao.lower().split("d")
    quantidade = int(partes[0]) if partes[0] else 1
    lados = int(partes[1])

    resultados = [random.randint(1, lados) for _ in range(quantidade)]
    soma = sum(resultados)
    total = soma + modificador

    return {
        "notacao": notacao,
        "modificador": modificador,
        "motivo": motivo,
        "resultados_individuais": resultados,
        "soma_dados": soma,
        "total": total,
        "critico": lados == 20 and soma == 20,
        "falha_critica": lados == 20 and soma == 1,
    }


def montar_system_prompt(personagem: dict, sessao: dict, sistema: dict) -> str:
    atributos = personagem.get("atributos", {})
    # Calcula modificadores D&D
    def mod(v): return (v - 10) // 2
    attrs = " | ".join(f"{k} {v} ({mod(v):+d})" for k, v in atributos.items())
    inventario = ", ".join(personagem.get("inventario", [])) or "nenhum"

    return f"""{sistema['contexto_narrador']}

## PERSONAGEM
Nome        : {personagem['nome']} ({personagem['raca']} {personagem['classe']})
Background  : {personagem['background']}
HP          : {personagem['hp_atual']}/{personagem['hp_maximo']}
Atributos   : {attrs}
Inventário  : {inventario}
Ouro        : {personagem.get('ouro', 0)} po

## HISTÓRIA DO PERSONAGEM
{personagem.get('resumo_background', '')}

## ESTADO DA SESSÃO
Localização : {sessao.get('localizacao', 'Início da aventura')}
Turno       : {sessao.get('turno', 0)}

## QUANDO ROLAR DADOS
- Ação arriscada ou com chance de falha → rolar_dado com 1d20 + modificador do atributo relevante
- Ataque → rolar_dado 1d20 para acertar, depois rolar dano se acertar
- Ação simples sem risco → narrar diretamente sem dados
- Após receber o resultado, narre a cena levando em conta se foi sucesso ou falha

## REGRAS DE NARRAÇÃO
- Respostas curtas (3 a 5 linhas) após receber os resultados dos dados
- Nunca decida ações pelo jogador
- Termine sempre descrevendo a situação atual
"""


async def narrar_stream(session_id: str, acao: str) -> AsyncGenerator[str, None]:
    """
    Loop agêntico com streaming:
    1. Chama a API com tools disponíveis
    2. Se o modelo pede rolar_dado → executa → envia evento SSE de rolagem → continua
    3. Quando o modelo gera texto → transmite token a token
    4. Salva o turno completo no MongoDB ao finalizar
    """
    db = get_db()

    sessao    = await db.sessions.find_one({"_id": session_id})
    personagem = await db.characters.find_one({"session_id": session_id})
    sistema   = await db.systems.find_one({"id": sessao["sistema_id"]})

    historico = sessao.get("historico_chat", [])[-20:]
    system    = montar_system_prompt(personagem, sessao, sistema)

    messages = (
        [{"role": "system", "content": system}]
        + historico
        + [{"role": "user", "content": acao}]
    )

    resposta_completa = ""

    while True:
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=[TOOL_ROLAR_DADO],
            tool_choice="auto",
            stream=True,
        )

        # Acumula deltas de tool_calls e texto
        tool_calls_acc = {}
        texto_chunk    = ""
        finish_reason  = None

        async for chunk in stream:
            choice = chunk.choices[0]
            finish_reason = choice.finish_reason or finish_reason
            delta = choice.delta

            # Fragmento de texto → transmite imediatamente
            if delta.content:
                texto_chunk   += delta.content
                resposta_completa += delta.content
                yield f"data: {json.dumps({'token': delta.content})}\n\n"

            # Fragmento de tool_call → acumula
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        tool_calls_acc[idx]["id"] = tc.id
                    if tc.function.name:
                        tool_calls_acc[idx]["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_calls_acc[idx]["function"]["arguments"] += tc.function.arguments

        # Modelo quer chamar ferramentas
        if finish_reason == "tool_calls":
            tool_calls_list = list(tool_calls_acc.values())

            # Adiciona a mensagem do assistente com os tool_calls ao histórico
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": tool_calls_list,
            })

            # Executa cada ferramenta e devolve o resultado
            for tc in tool_calls_list:
                args      = json.loads(tc["function"]["arguments"])
                resultado = executar_rolar_dado(**args)

                # Envia evento especial de rolagem para o frontend renderizar
                yield f"data: {json.dumps({'rolagem': resultado})}\n\n"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(resultado),
                })

            continue  # volta ao início do while para gerar a narrativa

        # Modelo terminou de gerar texto — sai do loop
        break

    # Persiste o turno no MongoDB
    await db.sessions.update_one(
        {"_id": session_id},
        {
            "$push": {
                "historico_chat": {
                    "$each": [
                        {"role": "user",      "content": acao},
                        {"role": "assistant", "content": resposta_completa},
                    ]
                }
            },
            "$inc": {"turno": 1},
            "$set": {"atualizado_em": datetime.datetime.utcnow()},
        },
    )
