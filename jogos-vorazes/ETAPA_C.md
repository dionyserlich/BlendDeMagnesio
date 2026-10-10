# Etapa C: preenchimento e paredes verticais

São dois projetos de teste, feitos a partir do projeto de produção aprovado na Etapa B (`variantes/Jogos_Vorazes_producao_4pecas.3mf`). **Cada um muda uma coisa só.** Ficam iguais em todos:
- as 4 cópias e suas posições;
- a aceleração 6000;
- o gerador Arachne e o `consistent_surface`;
- a malha.

A análise por trás das escolhas foi feita no código-fonte do Bambu Studio 02.08.02.60, com uma segunda verificação independente de cada tema.

| Arquivo | Muda | Ganho esperado por peça |
|---|---|---|
| `variantes/Jogos_Vorazes_producao_4pecas_C1_preenchimento.3mf` | `infill_combination` 0 → 1 e `sparse_infill_density` 15 % → 12 % | ~2,5–3,5 min |
| `variantes/Jogos_Vorazes_producao_4pecas_C2_paredes_verticais.3mf` | `ensure_vertical_shell_thickness` enabled → partial | ~3–6 min |

Os ganhos são projeções do meu simulador. Na Etapa B ele foi **pessimista**: projetou 47 min a mais por mesa que o Bambu. Então os números servem só para orientar; quem decide é o tempo do Bambu ao fatiar e o cronômetro.

**Por que dois arquivos.** As 4 cópias são instâncias de um mesmo objeto, então não dá para testar configurações diferentes na mesma mesa. Se as duas mudanças forem testadas juntas e aparecer algum defeito, não dá para saber qual delas causou. Por isso uma mesa de teste para cada. Se as duas passarem, junto as duas no projeto de produção.

## C1: preenchimento combinado + 12 %

- **O que muda.** O preenchimento esparso (gyroid) passa a ser feito a cada 2 camadas, numa passada de 0,32 mm. É impresso na camada de cima de cada par: 0,52 / 0,84 / 1,16 mm…
  - Paredes, sólidos internos, "Floating vertical shell" e pontes continuam sendo feitos em toda camada de 0,16 mm.
  - O desenho do gyroid e a largura da linha (0,45 mm) não mudam.
- **De onde vem o ganho.** O preenchimento desta peça é feito de movimentos curtos (82 % têm menos de 2 mm), e o tempo deles é gasto acelerando e freando, não pela velocidade máxima. Imprimir metade das passadas corta cerca de 1/3 desse tempo. A linha de 0,32 mm sai mais devagar (61,5 mm/s, limitada pelo fluxo de 7,5 mm³/s), mas isso quase não pesa.
- **Por que 12 % e não 10 %.** Com o preenchimento combinado, 10 % economiza só ~20 s a mais por peça. Em troca, os vãos do gyroid sobem de 4,5 para 5,4 mm, e nesta versão do Bambu não há opção que reforce o apoio das camadas sólidas de cima.
- **Riscos a olhar.**
  - Textura a cada 2 camadas ou desenho do preenchimento aparecendo na superfície. É mais provável entre Z 24 e 48 mm, onde o preenchimento corre colado à parede interna.
  - Furinhos nas pequenas superfícies de topo perto das cabeças (Z 56–64 mm).
- **Só para a produção de 4 peças.** No projeto de 1 peça, isso pode fazer a parede externa desacelerar em camadas alternadas e marcar o brilho. Não aplicar lá sem fatiar e conferir antes.

## C2: paredes verticais em "parcial"

- **O que muda.** No modo "enabled", o Bambu acrescenta uma faixa sólida estreita atrás das 2 paredes em toda superfície inclinada. No G-code ela aparece como "Floating vertical shell": 10,5 m e ~4 min por peça, em movimentos de 0,2 mm em média. O modo "partial" deixa de criar essas faixas. Continuam:
  - as 6 camadas sólidas sob qualquer topo;
  - as 4 camadas da base;
  - as pequenas áreas sólidas das cabeças.
- **Ganho esperado.** Cerca de 70 % do sólido interno da peça é essa faixa: ~550–775 mm³ que viram gyroid comum.
- **Risco a olhar.** O gyroid pode aparecer por baixo da casca nas encostas mais deitadas (40–75° em relação à mesa). Ali a casca passa a ser só as 2 paredes, ~0,6–0,8 mm, contra ~1,1–1,3 mm hoje. As regiões são:
  - os ombros do anel e o corpo do pássaro (Z 32–52 mm);
  - o lado de dentro do furo, na metade de baixo (Z 8–24 mm);
  - o topo das cabeças (Z 56–64 mm).

  **Controle:** a faixa do meio da altura (Z 20–28 mm) já é feita hoje com só 2 paredes mais gyroid. Se nela não aparece nada, é bom sinal.
- Se aparecer o desenho do preenchimento, volte para "enabled". Não compense com uma terceira parede: ela custaria mais tempo do que o "partial" economiza.

## Como fatiar

Faça igual à Etapa B:
1. Arquivo → Abrir projeto.
2. Não use "Organizar".
3. Não sincronize o filamento.
4. Envie com timelapse desligado.

Antes de imprimir, **fatie os dois e me mande a tela de "Estimativa de tempo" de cada um**. A referência é a Etapa B: 3h43m de impressão, ou 3h49m30s sem timelapse.

Confira também o cabeçalho do G-code:
- **C1:** `; infill_combination = 1` e `; sparse_infill_density = 12%`. Os blocos de preenchimento combinados aparecem com `; LAYER_HEIGHT: 0.32`.
- **C2:** `; ensure_vertical_shell_thickness = partial`.

Se quiser, mande o G-code compactado em `.zip` (ou o `.gcode.3mf`). Com ele eu confiro:
- **C1:** o comprimento do preenchimento deve cair de ~25,5 m para ~11–12 m por peça. Paredes e sólidos não podem mudar.
- **C2:** o volume de "Floating vertical shell" + sólido interno + ponte deve cair de ~1035 mm³ para ~250–450 mm³. Se ficar acima de ~500 mm³, o ganho é pequeno.

## Teste de impressão e critérios

Comece pela mesa de maior ganho no tempo do Bambu (provavelmente a C2). Compare com uma peça da Etapa B, do mesmo rolo.

| Critério | Como avaliar | Aprovado se |
|---|---|---|
| Brilho e superfície | Uma luz só, a 45°, peça girada em 4 posições, movendo o reflexo do silk sobre as encostas | Sem desenho de gyroid (passo de ~3–5 mm), sem textura a cada 2 camadas, sem faixas foscas. Mesmas faixas citadas acima |
| Topos e cabeças | Lupa em Z 56–64 mm | Sem furinhos nem "almofadas"; detalhes iguais aos da Etapa B |
| Rigidez | Apertar de leve as encostas e o anel | Igual à peça da Etapa B, sem ceder |
| Peso | Balança | C1: ~0,5 g a menos por peça. Queda bem maior indicaria subextrusão no preenchimento |
| Tempo | Cronômetro da mesa | Perto da estimativa do Bambu |

Se uma mudança passar e a outra não, a produção fica só com a que passou.
