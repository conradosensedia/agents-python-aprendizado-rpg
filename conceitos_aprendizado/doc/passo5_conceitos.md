# Passo 5 — Conceitos: RAG com Embeddings

## O que foi construído?

Um sistema que lê uma história pré-criada (10 chunks de lore) e injeta automaticamente apenas os trechos relevantes para cada ação do jogador — sem estourar o contexto da API.

---

## 1. O Problema que o RAG Resolve

Sem RAG, você tem duas opções ruins:

| Opção                        | Problema                                              |
|------------------------------|-------------------------------------------------------|
| Colocar todo o lore no prompt | Custa tokens em todo turno, pode estourar o contexto |
| Não colocar lore nenhum       | O narrador improvisa e contradiz a história           |

O RAG resolve isso com uma terceira opção: **injetar só o que é relevante agora**.

---

## 2. O que é um Embedding?

Um embedding é a conversão de um texto em um vetor de números que representa o seu **significado semântico**.

```python
gerar_embedding("Castelo de Valdris")  →  [0.21, -0.54, 0.87, ...]  # 1536 números
gerar_embedding("Fortaleza do rei")    →  [0.19, -0.51, 0.85, ...]  # próximo!
gerar_embedding("Receita de bolo")     →  [-0.43, 0.12, -0.33, ...]  # distante
```

Textos com significados parecidos geram vetores parecidos — mesmo usando palavras completamente diferentes. É por isso que buscar "usurpador" encontra o chunk sobre "Lord Kael" sem que a palavra apareça na consulta.

O modelo usado foi `text-embedding-3-small` da OpenAI:
- Gera vetores de 1536 dimensões
- É o modelo mais barato de embeddings da OpenAI
- Muito mais barato que gpt-4o-mini (centavos por mil documentos)

---

## 3. Similaridade Cosseno

A medida de "quão próximos" dois vetores são chama-se **similaridade cosseno**. Ela mede o ângulo entre dois vetores, não a distância absoluta.

```python
def similaridade_cosseno(vetor_a, vetor_b) -> float:
    a = np.array(vetor_a)
    b = np.array(vetor_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

Retorna um número entre -1 e 1:

| Score | Interpretação                    |
|-------|----------------------------------|
| ~1.0  | Textos quase idênticos           |
| ~0.8  | Muito relevantes                 |
| ~0.5  | Relacionados, mas vagamente      |
| ~0.2  | Pouco ou nada a ver              |

O cosseno é usado em vez da distância euclidiana porque ignora o comprimento dos vetores — só o **ângulo** (a direção do significado) importa.

---

## 4. Os Três Estágios do RAG

### Estágio 1 — Indexação (feita uma vez)
Transforma cada chunk de lore em vetor e salva em cache.

```python
for chunk in chunks:
    chunk["embedding"] = gerar_embedding(chunk["texto"])

# Salva em disco para não repetir o custo
json.dump(cache, arquivo)
```

Sem cache, você pagaria pela geração de embeddings a cada vez que o programa iniciar. Com cache, paga uma vez e reutiliza para sempre (ou até o lore mudar).

### Estágio 2 — Retrieval (a cada turno)
Converte a ação do jogador em vetor e compara com todos os chunks.

```python
vetor_consulta = gerar_embedding(acao_do_jogador)

for chunk in chunks:
    score = similaridade_cosseno(vetor_consulta, chunk["embedding"])

# Retorna os top_k chunks com maior score
```

### Estágio 3 — Augmented Generation
Injeta apenas os chunks recuperados no system prompt, não o lore inteiro.

```python
lore_injetado = "\n\n".join(chunk["texto"] for chunk in chunks_relevantes)
system = f"""...
## CONTEXTO DO MUNDO
{lore_injetado}
..."""
```

---

## 5. Chunking — Como Dividir o Lore

"Chunk" é cada pedaço do lore que vira um vetor. A divisão importa:

| Chunk muito grande | Chunk muito pequeno        |
|--------------------|----------------------------|
| Recupera contexto demais, injeta tokens desnecessários | Perde contexto, o modelo não entende sem o entorno |

A regra prática: **um chunk = um conceito coeso**. No RPG, cada chunk é um tópico do mundo (um lugar, um personagem, um evento histórico). Em sistemas reais, chunks de 200-500 tokens funcionam bem.

---

## 6. O Cache de Embeddings

Gerar embeddings tem custo (tempo + dinheiro). O cache evita repetir isso:

```
Primeira execução:
  lore_valdris.json → API embeddings → lore_embeddings_cache.json

Execuções seguintes:
  lore_embeddings_cache.json → carrega direto (sem chamada à API)
```

O arquivo `lore_embeddings_cache.json` que você abriu no IDE é exatamente isso: os 10 chunks com seus vetores de 1536 números cada, prontos para uso sem chamar a API.

---

## 7. Custo por Turno com e sem RAG

Lore com 10 chunks (~1.000 tokens totais):

| Abordagem      | Tokens no prompt por turno |
|----------------|---------------------------|
| Sem RAG (tudo) | ~1.000 tokens              |
| Com RAG top-2  | ~200 tokens                |

Em um lore real com 100 páginas (~75.000 tokens), injetar tudo seria inviável. O RAG torna possível ter uma história rica sem pagar por ela em cada turno.

---

## 8. Busca Semântica vs. Busca por Palavra-Chave

| Busca por palavra-chave        | Busca por embedding (RAG)           |
|--------------------------------|--------------------------------------|
| "castelo" só encontra "castelo" | "castelo" encontra "fortaleza", "torre", "muralha" |
| Rápida, sem custo de API        | Requer chamada à API por consulta    |
| Frágil a sinônimos              | Robusta a variações de linguagem     |
| Boa para filtros exatos         | Boa para busca por intenção          |

---

## Resumo: o que mudou do Passo 4 para o Passo 5

| Aspecto             | Passo 4                        | Passo 5                              |
|---------------------|--------------------------------|--------------------------------------|
| Conhecimento do mundo | Estado do jogo (dicionários) | Estado + lore histórico (chunks)     |
| Injeção de contexto | System prompt fixo             | Chunks selecionados dinamicamente    |
| Custo por turno     | Fixo                           | Proporcional ao top_k (controlável) |
| Chamadas à API      | 1 por turno (chat)             | 2 por turno (embedding + chat)       |
| Busca              | Nenhuma                        | Semântica por similaridade cosseno   |
| Arquivo novo        | Nenhum                         | lore.json + cache de embeddings      |