# Passo 3 — Conceitos: System Prompt Dinâmico

## O que foi construído?

Um narrador que conhece o estado do jogo — HP do personagem, localização, inventário — porque essas informações são injetadas no system prompt antes de cada chamada.

---

## 1. O Prompt como Interface com o Mundo

O modelo não tem acesso a variáveis Python, banco de dados ou qualquer estado externo. A única forma de ele "saber" algo é se esse algo estiver escrito no texto que você envia.

```
Estado Python (a verdade)     →     System Prompt (o que o modelo vê)
─────────────────────────────       ────────────────────────────────
personagem["hp"] = 5          →     "HP: 5/20"
mundo["localizacao"] = "..."  →     "Localização: Catacumbas Sombrias"
personagem["inventario"]      →     "Inventário: espada, tocha"
```

Esta tradução — de estado para texto — é responsabilidade do seu código, não do modelo.

---

## 2. Separação entre Estado e Representação

O projeto agora tem duas camadas distintas:

**Camada de estado** — dicionários Python, a fonte da verdade:
```python
personagem = {"nome": "Aldric", "hp": 5, "hp_max": 20, ...}
mundo = {"localizacao": "Catacumbas", "hora": "noite", ...}
```

**Camada de representação** — a função que transforma estado em texto:
```python
def montar_system_prompt(personagem, mundo) -> str:
    return f"""
    HP: {personagem['hp']}/{personagem['hp_max']}
    Localização: {mundo['localizacao']}
    ...
    """
```

Quando o HP muda, você atualiza o dicionário. O prompt reflete isso automaticamente na próxima chamada. O modelo nunca sabe que existem dicionários — ele só vê o texto.

---

## 3. System Prompt Reconstruído a Cada Turno

No Passo 2, o system era fixo e entrava uma vez. Agora ele é reconstruído antes de cada chamada:

```python
# A cada turno:
system_atual = montar_system_prompt(personagem, mundo)  # estado fresco

messages = [{"role": "system", "content": system_atual}] + historico + [acao_atual]
```

O histórico de diálogos (`historico`) continua crescendo normalmente. O que muda é que o system carrega sempre os valores mais recentes do jogo.

---

## 4. Comportamento Emergente via Contexto

Quando o personagem tem 5/20 HP, o narrador descreve cansaço e ferimentos — não porque foi programado para isso, mas porque o HP está no prompt e o modelo infere o significado.

Isso é **comportamento emergente via contexto**: você não precisa programar cada reação. Basta garantir que a informação relevante esteja no prompt; o modelo interpreta e age coerentemente.

Quanto mais rico e preciso o contexto que você injeta, mais inteligente o agente parece.

---

## 5. Esta é a Base de Todo Agente RAG

Este padrão — buscar informação externa e injetá-la no prompt — é a essência do **RAG (Retrieval-Augmented Generation)**, usado em sistemas reais como:

- Chatbots que consultam documentos da empresa
- Assistentes que leem e-mails antes de responder
- Agentes que verificam o estado de um banco de dados

No RPG, o "banco de dados" é o dicionário do personagem. Em produção, pode ser um banco vetorial com milhões de documentos. O mecanismo é o mesmo.

---

## 6. Estrutura das Mensagens por Turno

```
Turno N:
┌─────────────────────────────────────────────────────┐
│ system  → montar_system_prompt(estado_atual)        │  ← sempre fresco
│ user    → "Entro na taverna"                        │  ┐
│ assistant → "A porta range..."                      │  │ histórico
│ user    → "Falo com o bardo"                        │  │ acumulado
│ assistant → "O bardo levanta os olhos..."           │  ┘
│ user    → [ação do turno atual]                     │  ← nova entrada
└─────────────────────────────────────────────────────┘
```

---

## Resumo: o que mudou do Passo 2 para o Passo 3

| Aspecto            | Passo 2                  | Passo 3                          |
|--------------------|--------------------------|----------------------------------|
| System prompt      | Texto fixo               | Reconstruído a cada turno        |
| Estado do jogo     | Inexistente              | Dicionários Python               |
| Conhecimento do modelo | Só o que foi dito   | Estado atual + histórico         |
| Comportamento      | Genérico                 | Contextual (HP, local, itens)    |
| Função central     | Nenhuma                  | `montar_system_prompt()`         |
