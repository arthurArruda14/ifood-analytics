# 🍔 Delivery Analytics AI

Dashboard em que você **pergunta em português** sobre dados de pedidos de delivery e recebe **números, gráficos e uma explicação em linguagem de negócio**, tudo gerado por IA.

> Projeto de portfólio inspirado em problemas reais de operações de delivery. Os dados são **sintéticos** (gerados por `src/data.py`), nenhum dado real de empresa é usado.

<!-- Troque pelo seu GIF/print depois de rodar o app -->
<!-- ![Demo](docs/demo.gif) -->

**Demo no ar:** _adicione aqui o link do Streamlit Cloud_

## O problema

Analistas e gestores de operações perdem horas pedindo relatórios e montando gráficos para responder perguntas simples como *"o que causa mais atraso?"*. Este projeto reduz isso para segundos: a pessoa pergunta, a IA escreve a análise, o app executa e explica.

## Como funciona

```
Pergunta  ──►  LLM gera código pandas  ──►  Validação de segurança (AST)
                                                      │
        Explicação em PT-BR  ◄──  LLM resume  ◄──  Execução  ──(erro?)──► 1 retry com o erro
```

1. **Geração de código:** o LLM recebe só o *esquema* dos dados (colunas, tipos, exemplos), nunca a base inteira.
2. **Validação:** o código passa por uma análise da árvore sintática (`ast`) que bloqueia imports, acesso a arquivos, `eval/exec` e atributos privados.
3. **Execução:** roda com `builtins` restritos e uma cópia do DataFrame.
4. **Auto-correção:** se falhar, o erro volta ao LLM para uma segunda tentativa.
5. **Explicação:** um segundo prompt traduz o resultado em até 4 frases com uma sugestão de ação.

Os prompts estão versionados em [`prompts/`](prompts/), com o raciocínio de cada regra.

## Insights que o dataset de exemplo permite descobrir

Com 5.000 pedidos sintéticos (semente fixa), perguntas como estas retornam:

| Pergunta | Resultado |
|---|---|
| Taxa de atraso geral | 27,8% |
| Atraso com chuva vs. sol | 74,1% vs. 16,4% |
| Horários de pico de atraso | 13h, 19h, 20h e 21h (37% a 39%) |
| Tempo médio de entrega com chuva | 45,2 min (vs. 36,2 min com sol) |

## Stack

Python · Streamlit · pandas · Plotly · API da Anthropic (Claude) · pytest

## Como rodar

```bash
git clone https://github.com/arthur_arruda/ifood-analytics-ai.git
cd ifood-analytics-ai

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # coloque sua ANTHROPIC_API_KEY no .env
streamlit run app.py
```

Para gerar o CSV de exemplo manualmente: `python -m src.data`.
Para rodar os testes: `pytest`.

## Estrutura

```
├── app.py                 # Interface Streamlit
├── src/
│   ├── data.py            # Carregamento de CSV e gerador de dados sintéticos
│   ├── llm.py             # Chamadas ao LLM (gerar código / explicar resultado)
│   ├── pipeline.py        # Orquestração com retry
│   └── safe_exec.py       # Validação e execução restrita do código gerado
├── prompts/               # Prompts versionados e documentados
├── tests/                 # Testes de segurança e dados
└── docs/                  # Prints e GIFs da demo
```

## Decisões e limitações

- **Segurança:** executar código gerado por IA é arriscado. A validação por `ast` reduz o risco, mas **não é um sandbox completo**. Em produção, eu rodaria o código em contêiner isolado com limite de tempo e memória.
- **Privacidade:** apenas o esquema e exemplos de valores são enviados ao modelo, não a base inteira.
- **Alucinação:** a explicação é gerada a partir do resultado real da execução, e o código fica visível para auditoria.
- **Dados sintéticos:** os padrões (chuva e horário de pico aumentando atrasos) foram embutidos de propósito para a demo.

## Próximos passos

- [ ] Memória de conversa para perguntas de acompanhamento ("e só na chuva?")
- [ ] Execução em contêiner Docker isolado
- [ ] Avaliação automática com um conjunto de perguntas e respostas esperadas
- [ ] Deploy no Streamlit Community Cloud

## Autor

**Arthur Marangoni de Arruda** · ADS na Fatec Taquaritinga · [LinkedIn](https://www.linkedin.com/in/arthur-arruda-b0abb21a5/)
