# Passo 7 — Conceitos: Streaming

## O que foi construído?

Uma comparação direta entre chamada normal e streaming, seguida de um loop de jogo onde o texto do narrador aparece palavra por palavra conforme o modelo gera.

---

## 1. O que é Streaming?

Sem streaming, a API processa a resposta inteira no servidor e envia tudo de uma vez. Com streaming, a API envia cada fragmento (token) conforme gera — como água saindo de uma torneira, não de um balde.

```
Sem streaming:  [espera 3s] → "A floresta sombria se abre diante de você..."
Com streaming:  "A" → " floresta" → " sombria" → " se" → " abre" → ...
```

O tempo total é o mesmo. O que muda é quando o usuário começa a ver o texto.

---

## 2. A Única Mudança na Chamada à API

Ativar streaming requer apenas um parâmetro:

```python
# Sem streaming
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
)
texto = response.choices[0].message.content  # acessa depois de tudo chegar

# Com streaming
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    stream=True,                              # <-- única mudança
)
for chunk in stream:                          # itera conforme chega
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

A diferença de implementação é mínima. A diferença de experiência para o usuário é enorme.

---

## 3. A Estrutura do Chunk

Cada fragmento recebido no loop é um objeto com estrutura similar à resposta normal, mas com `delta` no lugar de `message`:

```
chunk.choices[0].delta.content   →  fragmento de texto (pode ser None no último)
chunk.choices[0].finish_reason   →  None durante a geração, "stop" no último chunk
```

O `if delta:` antes de usar o conteúdo é necessário porque o último chunk tem `content = None` para sinalizar o fim.

---

## 4. Acumulando o Texto Completo

Com streaming, você não tem o texto completo disponível de imediato — precisa acumular:

```python
texto_completo = ""

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)  # exibe em tempo real
        texto_completo += delta            # acumula para uso posterior

# Aqui texto_completo tem a resposta inteira — usa no histórico
historico.append({"role": "assistant", "content": texto_completo})
```

Sem acumular, você perde a resposta após exibi-la e não consegue adicioná-la ao histórico.

---

## 5. `flush=True` — Por que é Necessário

Por padrão, o Python armazena a saída em buffer antes de imprimir — espera acumular um bloco antes de mandar para o terminal. Com `flush=True`, você força a impressão imediata de cada fragmento:

```python
print(delta, end="", flush=True)
#            ↑              ↑
#      sem quebra      imprime agora
#      de linha        sem esperar buffer
```

Sem `flush=True`, o efeito de streaming some — o terminal ainda esperaria e mostraria tudo de uma vez.

---

## 6. Por que Streaming Importa para uma Plataforma

| Situação                  | Sem streaming              | Com streaming                  |
|---------------------------|----------------------------|--------------------------------|
| Resposta de 5 linhas      | Tela vazia por 3s, depois tudo | Texto aparece em ~0.3s        |
| Resposta de 20 linhas     | Tela vazia por 8s          | Usuário lê enquanto o modelo gera |
| Usuário quer cancelar     | Não consegue               | Pode interromper no meio       |
| Interface web             | Precisa de polling          | WebSocket natural com SSE      |

Em qualquer produto com LLM voltado a usuários reais, streaming não é opcional — é o padrão esperado.

---

## 7. Streaming com Tool Use

Streaming e tool use podem coexistir, mas requerem tratamento especial: os `tool_calls` também chegam em fragmentos e precisam ser acumulados antes de executar a função. Frameworks como LangChain e LlamaIndex abstraem isso, mas a lógica subjacente é a mesma: acumular os deltas até ter o JSON completo do tool call.

---

## Resumo: sem vs. com streaming

| Aspecto              | Sem streaming                  | Com streaming                     |
|----------------------|--------------------------------|-----------------------------------|
| Parâmetro na API     | (ausente)                      | `stream=True`                     |
| Acesso ao texto      | `response.choices[0].message.content` | Loop `for chunk in stream`  |
| Quando o usuário vê  | Após processamento completo    | Token a token, em tempo real      |
| Acumular texto       | Desnecessário                  | Obrigatório para usar no histórico|
| `flush=True`         | Irrelevante                    | Necessário para efeito visual     |
| Tempo total          | Igual                          | Igual                             |
| Percepção de rapidez | Lenta                          | Rápida                            |