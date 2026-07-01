# Passo 8 — Conceitos: Persistência de Estado

## O que foi construído?

Um sistema completo de save/load: o jogador pode sair e voltar dias depois com o personagem, inventário, localização e histórico da conversa exatamente onde estavam. O jogo também salva automaticamente a cada 5 turnos.

---

## 1. O Problema da Falta de Persistência

Sem persistência, toda vez que o programa fecha:
- A ficha do personagem é perdida
- O inventário é perdido
- A localização volta ao início
- O histórico do chat some — o narrador "esquece" tudo

Persistência é o que transforma um script em um produto. Um jogador não pode investir horas numa campanha se tudo se perde ao fechar o terminal.

---

## 2. O que Precisa Ser Salvo

Nem tudo precisa ser persistido. A regra é: **salve tudo que não pode ser reconstruído**.

| O que salvar             | Por quê                                          |
|--------------------------|--------------------------------------------------|
| `personagem`             | HP, inventário e atributos mudam durante o jogo  |
| `mundo.localizacao`      | O jogador pode estar em qualquer lugar           |
| `mundo.eventos`          | Registro leve do que aconteceu (memória do mundo)|
| `historico_chat`         | Para o narrador lembrar a sessão ao retomar      |
| `meta` (id, turnos, data)| Para listar e identificar os saves               |

| O que NÃO salvar         | Por quê                                          |
|--------------------------|--------------------------------------------------|
| System prompt            | É reconstruído dinamicamente a partir do estado  |
| Embeddings do lore       | Já têm cache próprio no ChromaDB                 |
| Configurações da API     | Vêm do `.env`                                    |

---

## 3. JSON como Formato de Save

JSON foi escolhido por três motivos:

1. **Legível** — você abre o arquivo e entende o estado do jogo sem ferramentas especiais
2. **Editável** — dá para corrigir o HP ou dar um item direto no arquivo se quiser
3. **Sem dependências** — `json` é biblioteca padrão do Python

```python
# Salvar
arquivo.write_text(json.dumps(estado, ensure_ascii=False, indent=2))

# Carregar
estado = json.loads(arquivo.read_text(encoding="utf-8"))
```

A única limitação do JSON é que não suporta tipos Python como `datetime` diretamente — por isso salvamos datas como string ISO (`datetime.now().isoformat()`).

---

## 4. Estrutura do Save

O estado é um único dicionário com quatro seções claras:

```python
{
    "meta": {
        "id": "uuid único",          # identifica o save
        "criado_em": "2026-06-30T...",
        "salvo_em": "2026-06-30T...",
        "turnos": 12,
    },
    "personagem": {
        "nome": "Aldric",
        "hp": 14,
        "inventario": ["espada", "tocha"],
        ...
    },
    "mundo": {
        "localizacao": "Catacumbas",
        "eventos": ["Encontrou Brenna", "Descobriu a passagem secreta"],
        ...
    },
    "historico_chat": [
        {"role": "user", "content": "Entro na taverna"},
        {"role": "assistant", "content": "A porta range..."},
        ...
    ]
}
```

Cada seção tem responsabilidade única. Quando o HP muda, só `personagem.hp` é atualizado. Quando a localização muda, só `mundo.localizacao`. O estado nunca é duplicado em lugares diferentes.

---

## 5. UUID como Identificador de Save

Cada save recebe um `uuid4()` como identificador — um número aleatório de 128 bits que é praticamente impossível de repetir:

```python
import uuid
estado["meta"]["id"] = str(uuid.uuid4())
# → "a3f8c2d1-4b7e-4f9a-8c3d-1e2f5b6a7c8d"
```

O nome do arquivo é o próprio UUID: `a3f8c2d1-...json`. Isso garante que dois personagens com o mesmo nome nunca sobrescrevam o save um do outro.

---

## 6. Autosave

Salvar manualmente é fácil de esquecer. O autosave garante que o progresso nunca é perdido completamente:

```python
if estado["meta"]["turnos"] % 5 == 0:
    salvar(estado)
    print(f"[autosave — turno {estado['meta']['turnos']}]")
```

O operador `%` (módulo) retorna o resto da divisão — quando `turnos` é múltiplo de 5, o resto é 0 e o save ocorre. Em produtos reais, o autosave costuma acontecer em eventos importantes (troca de área, fim de combate) em vez de por contagem de turnos.

---

## 7. Truncagem do Histórico de Chat

O histórico completo pode crescer indefinidamente e estourar o contexto da API. A solução é enviar apenas as mensagens mais recentes:

```python
messages = (
    [{"role": "system", "content": system}]
    + estado["historico_chat"][-20:]   # últimas 10 trocas (20 mensagens)
    + [{"role": "user", "content": acao}]
)
```

O histórico completo continua salvo no JSON — você não perde nada. Mas a API só recebe as últimas 20 mensagens. O que aconteceu antes fica acessível via:
- `mundo.eventos` — registro leve dos momentos importantes
- ChromaDB — se integrado (Passo 6), permite busca semântica no passado distante

---

## 8. Retomada com Resumo

Quando um save é carregado, o narrador é chamado para resumir onde a história estava:

```python
resposta = chamar_narrador([
    {"role": "system", "content": montar_system_prompt(estado)},
    {"role": "user", "content": "Resuma brevemente onde estávamos e o que acabou de acontecer."},
])
```

Isso aproveita o histórico salvo como contexto para o modelo gerar um resumo coerente — o jogador não precisa lembrar sozinho onde parou.

---

## Resumo: o que mudou do Passo 7 para o Passo 8

| Aspecto               | Passo 7                     | Passo 8                              |
|-----------------------|-----------------------------|--------------------------------------|
| Duração de uma sessão | Só enquanto o programa roda | Persiste entre sessões               |
| Estado do personagem  | Resetado a cada execução    | Salvo e carregado do disco           |
| Histórico do chat     | Perdido ao fechar           | Salvo no JSON                        |
| Múltiplos personagens | Impossível                  | Um arquivo JSON por personagem       |
| Identificação do save | Nenhuma                     | UUID único por jogo                  |
| Proteção contra perda | Nenhuma                     | Autosave a cada 5 turnos             |
| Retomada              | Começa do zero              | Narrador resume onde parou           |
