# Passo 4 — Conceitos: Tool Use (Uso de Ferramentas)

## O que foi construído?

Um narrador que não apenas fala — ele age. Antes de responder, o modelo pode chamar funções Python como `rolar_dado()`, `verificar_habilidade()` e `atualizar_hp()` de forma autônoma, usando os resultados para compor a narrativa.

---

## 1. O que é Tool Use?

Tool use é a capacidade do modelo de solicitar a execução de funções externas durante uma resposta.

O modelo **não executa** as funções — ele declara a intenção de chamá-las. Seu código executa e devolve o resultado. O modelo então usa esse resultado para continuar.

```
Sem tools:  você → [mensagens] → API → texto final

Com tools:  você → [mensagens + tools] → API → "chame rolar_dado(20)"
                                              ↓
                                       você executa → resultado: 17
                                              ↓
                                   você → [mensagens + resultado] → API → texto final
```

---

## 2. O Schema das Ferramentas

O modelo não vê código Python. Ele vê um schema JSON que descreve cada ferramenta: nome, o que faz e quais parâmetros aceita. É a "documentação" que ensina ao modelo quando e como chamar cada função.

```python
{
    "type": "function",
    "function": {
        "name": "rolar_dado",
        "description": "Rola um dado de N lados. Use para ações com sorte ou risco.",
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
}
```

Três campos são críticos:
| Campo         | Função                                                        |
|---------------|---------------------------------------------------------------|
| `name`        | Identificador usado para despachar a função correta           |
| `description` | O modelo lê isso para decidir se deve ou não usar a ferramenta |
| `parameters`  | Define os argumentos — o modelo os preenche automaticamente   |

A qualidade da `description` determina quando o modelo usa a ferramenta. Uma descrição ruim leva a tool calls desnecessários ou à falta deles quando precisaria.

---

## 3. O Loop Agêntico

Esta é a estrutura mais importante do passo 4. O modelo pode pedir várias ferramentas antes de dar uma resposta final — e cada resultado volta como contexto para a próxima decisão.

```python
def chamar_narrador(messages):
    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS_SCHEMA,
        )
        msg = response.choices[0].message

        if msg.tool_calls:           # modelo quer chamar uma ferramenta
            messages.append(msg)     # registra a intenção no histórico

            for tool_call in msg.tool_calls:
                resultado = executar(tool_call)   # você executa
                messages.append({                 # devolve o resultado
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(resultado),
                })
            continue                 # volta ao início: chama a API de novo

        return msg.content           # resposta final de texto — sai do loop
```

O `while True` só termina quando o modelo devolve texto puro, sem `tool_calls`. Isso pode levar 1, 2 ou mais chamadas à API numa única ação do jogador.

---

## 4. O Role `tool` nas Mensagens

Depois do Passo 4, a lista `messages` tem um quarto tipo de role:

| Role        | Quando aparece                                      |
|-------------|-----------------------------------------------------|
| `system`    | Instruções permanentes do narrador                  |
| `user`      | Ação do jogador                                     |
| `assistant` | Resposta do modelo (texto ou intenção de tool call) |
| `tool`      | Resultado de uma ferramenta executada pelo seu código |

Uma sequência real no histórico fica assim:

```
user      → "Ataco o guarda"
assistant → tool_calls: [atualizar_hp(-6), rolar_dado(20)]
tool      → {"hp_antes": 20, "hp_depois": 14, ...}
tool      → {"resultado": 15, "lados": 20}
assistant → "Seu golpe corta o ombro do guarda..."   ← resposta final
```

---

## 5. Despacho de Funções (Function Dispatch)

O modelo devolve o nome da função como string. Você precisa de um mapa para encontrar e executar a função correta:

```python
FERRAMENTAS_DISPONIVEIS = {
    "rolar_dado": rolar_dado,
    "verificar_habilidade": verificar_habilidade,
    "atualizar_hp": atualizar_hp,
    "adicionar_item": adicionar_item,
}

# Na hora de executar:
nome = tool_call.function.name
args = json.loads(tool_call.function.arguments)
resultado = FERRAMENTAS_DISPONIVEIS[nome](**args)
```

Este padrão de dicionário `nome → função` é o **dispatcher** — presente em praticamente todo sistema que implementa tool use.

---

## 6. `tool_choice` — Controle sobre o uso de ferramentas

O parâmetro `tool_choice` define quando o modelo pode usar ferramentas:

| Valor          | Comportamento                                         |
|----------------|-------------------------------------------------------|
| `"auto"`       | O modelo decide se usa ou não (mais comum)            |
| `"required"`   | O modelo é obrigado a chamar pelo menos uma ferramenta |
| `"none"`       | O modelo não pode usar nenhuma ferramenta             |
| `{"type": "function", "function": {"name": "X"}}` | Força uma ferramenta específica |

No RPG usamos `"auto"` — para narração simples o modelo responde direto; para ações com risco ele chama as ferramentas.

---

## 7. Efeitos Colaterais Reais

Uma ferramenta pode ter **efeito colateral real** — modificar o estado do jogo fora do modelo:

```python
def atualizar_hp(quantidade: int) -> dict:
    personagem["hp"] = max(0, personagem["hp"] + quantidade)  # muda o estado real
    return {"hp_depois": personagem["hp"]}
```

O modelo não sabe que existe um dicionário Python sendo alterado. Ele só vê o resultado que você devolveu. Mas na próxima chamada, o system prompt atualizado vai refletir o novo HP — fechando o ciclo entre tool use e estado do jogo.

---

## Resumo: o que mudou do Passo 3 para o Passo 4

| Aspecto               | Passo 3                    | Passo 4                              |
|-----------------------|----------------------------|--------------------------------------|
| O modelo pode         | Apenas gerar texto         | Gerar texto e solicitar funções      |
| Chamadas por turno    | Sempre 1                   | 1 ou mais (loop agêntico)            |
| Roles nas mensagens   | system, user, assistant    | + tool                               |
| Estado do jogo muda   | Só por comando do jogador  | Também por decisão do modelo         |
| Função central        | `montar_system_prompt()`   | `chamar_narrador()` com while loop   |
| Conceito central      | Prompt como interface      | Agente que percebe, decide e age     |
