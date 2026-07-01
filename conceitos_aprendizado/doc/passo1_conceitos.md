# Passo 1 — Conceitos: Uma Chamada à API

## O que acontece quando você chama um LLM?

Você envia uma lista de mensagens e recebe uma resposta. Não existe "sessão" no servidor — cada chamada é independente e stateless. Toda a memória da conversa mora no seu código, não no modelo.

---

## 1. Messages — A estrutura fundamental

Toda chamada à API é uma lista de dicionários. A ordem importa: é a cronologia da conversa.

```python
messages = [
    {"role": "system",    "content": "Você é um narrador..."},
    {"role": "user",      "content": "Eu entro na taverna."},
]
```

Cada dicionário tem dois campos obrigatórios:

| Campo     | O que é                                      |
|-----------|----------------------------------------------|
| `role`    | Quem está falando (`system`, `user`, `assistant`) |
| `content` | O texto da mensagem                          |

---

## 2. Roles — Quem fala o quê

### `system`
A instrução permanente que molda o comportamento do modelo durante toda a conversa. É onde você define a "personalidade" e as regras. O modelo trata isso como uma diretriz de alto nível.

```python
{"role": "system", "content": "Você é um narrador de RPG. Seja atmosférico e breve."}
```

### `user`
O que o jogador digitou. É a entrada humana.

```python
{"role": "user", "content": "Eu entro na taverna."}
```

### `assistant`
O que o modelo respondeu em turnos anteriores. Quando você quiser que o modelo lembre o que disse antes, precisa incluir as respostas antigas na lista com este role. Isso será o foco do Passo 2.

```python
{"role": "assistant", "content": "A porta range. Um bardo toca no canto..."}
```

---

## 3. O objeto de resposta

A API devolve um objeto rico, não apenas texto. Os campos mais importantes:

```python
response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

response.choices[0].message.content  # o texto gerado
response.model                        # modelo que processou a requisição
response.usage.prompt_tokens          # tokens consumidos pela entrada
response.usage.completion_tokens      # tokens consumidos pela saída
response.usage.total_tokens           # soma dos dois
```

**Por que tokens importam?** Você paga por token. Quanto mais longo o histórico de mensagens, mais caro fica cada chamada. Gerenciar o tamanho da lista `messages` é uma das principais preocupações de sistemas com agentes.

---

## 4. Variáveis de ambiente e `.env`

Nunca coloque chaves de API diretamente no código — elas podem vazar via git, logs ou prints acidentais.

O padrão é:
1. Guardar a chave em um arquivo `.env` (que fica no `.gitignore`)
2. Carregar no início do script com `load_dotenv()`
3. O SDK lê automaticamente a variável de ambiente `OPENAI_API_KEY`

```python
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()  # encontra a chave no ambiente, não no código
```

---

## 5. Stateless — O insight mais importante

O modelo **não lembra** de nada entre chamadas. Se você fizer duas chamadas separadas, a segunda não sabe que a primeira existiu.

```
Chamada 1: [system, user("entro na taverna")]      → resposta A
Chamada 2: [system, user("falo com o bardo")]      → modelo não sabe da taverna!
```

Para simular memória, você precisa reenviar todo o histórico a cada chamada:

```
Chamada 2: [system, user("entro na taverna"), assistant(resposta A), user("falo com o bardo")]
```

Isso é exatamente o que o Passo 2 implementa: o loop de conversa.