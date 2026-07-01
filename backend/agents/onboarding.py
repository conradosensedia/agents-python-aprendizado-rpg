"""
Agente de Onboarding — criação de personagem via conversa.

Responsabilidades:
- Guiar o jogador na criação do personagem de forma conversacional
- Coletar nome, raça, classe, background e atributos
- Detectar quando a ficha está completa e extraí-la como JSON estruturado
- Salvar o personagem no MongoDB
"""

import json
from openai import AsyncOpenAI
from database.mongo import get_db

client = AsyncOpenAI()

TOOL_FINALIZAR = {
    "type": "function",
    "function": {
        "name": "finalizar_personagem",
        "description": "Chame esta função APENAS quando o jogador tiver definido nome, raça, classe, background e todos os 6 atributos. Salva a ficha completa.",
        "parameters": {
            "type": "object",
            "properties": {
                "nome":       {"type": "string", "description": "Nome do personagem"},
                "raca":       {"type": "string", "description": "Raça do personagem"},
                "classe":     {"type": "string", "description": "Classe do personagem"},
                "background": {"type": "string", "description": "Background do personagem"},
                "atributos": {
                    "type": "object",
                    "description": "Os 6 atributos com valores entre 8 e 15",
                    "properties": {
                        "Força":         {"type": "integer"},
                        "Destreza":      {"type": "integer"},
                        "Constituição":  {"type": "integer"},
                        "Inteligência":  {"type": "integer"},
                        "Sabedoria":     {"type": "integer"},
                        "Carisma":       {"type": "integer"}
                    },
                    "required": ["Força", "Destreza", "Constituição", "Inteligência", "Sabedoria", "Carisma"]
                },
                "hp_maximo":      {"type": "integer", "description": "HP máximo inicial"},
                "resumo_background": {"type": "string", "description": "2 linhas sobre a história do personagem"}
            },
            "required": ["nome", "raca", "classe", "background", "atributos", "hp_maximo", "resumo_background"]
        }
    }
}


async def processar_turno(session_id: str, historico: list, sistema: dict) -> dict:
    """
    Processa um turno do onboarding.
    Retorna {"tipo": "mensagem", "conteudo": "..."} durante a conversa
    ou {"tipo": "concluido", "personagem": {...}} quando a ficha estiver pronta.
    """
    system_prompt = f"""{sistema['contexto_onboarding']}

Raças disponíveis: {', '.join(sistema['racas'])}
Classes disponíveis: {', '.join(sistema['classes'])}
Backgrounds disponíveis: {', '.join(sistema['backgrounds'])}

HP inicial = dado da classe + modificador de Constituição.
Dados por classe: {json.dumps(sistema['hp_base_por_classe'], ensure_ascii=False)}

Quando o jogador tiver decidido TUDO (nome, raça, classe, background e 6 atributos),
chame a função finalizar_personagem com os dados completos.
"""

    # __inicio__ é um gatilho interno — substitui por uma instrução ao agente
    historico_processado = []
    for msg in historico:
        if msg["role"] == "user" and msg["content"] == "__inicio__":
            historico_processado.append({"role": "user", "content": "Inicie a criação do personagem com uma saudação breve e já faça a primeira pergunta."})
        else:
            historico_processado.append(msg)

    messages = [{"role": "system", "content": system_prompt}] + historico_processado

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=[TOOL_FINALIZAR],
        tool_choice="auto",
    )

    msg = response.choices[0].message

    # Agente quer finalizar a ficha
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        personagem = json.loads(tool_call.function.arguments)
        personagem["session_id"] = session_id
        personagem["inventario"] = []
        personagem["hp_atual"] = personagem["hp_maximo"]
        personagem["ouro"] = 10

        db = get_db()
        await db.characters.insert_one(personagem)

        return {"tipo": "concluido", "personagem": personagem}

    # Agente quer continuar a conversa
    return {"tipo": "mensagem", "conteudo": msg.content}
