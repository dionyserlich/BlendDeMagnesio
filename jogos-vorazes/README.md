# Jogos Vorazes (tordo + serpente) — otimização para Bambu Lab A1

Impressora Bambu Lab A1, bico 0,4 mm, PLA Silk dourado Masterprint (perfil "Generic PLA Silk @BBL A1": 220 °C, 7,5 mm³/s).
Peça: cerca de 32 × 66 × 64 mm, malha de 976 mil triângulos, 400 camadas de 0,16 mm, suporte em árvore.

## Arquivos

| Arquivo | Para quê |
|---|---|
| `original/Jogos_Vorazes_malha_suavizada-02.3mf` | Projeto original, **idêntico byte a byte** ao enviado (sha256 `79af27a3…c1a4`). |
| `original/Jogos_Vorazes_furos_1-03mm_PLA_1h27m.gcode` | G-code original fatiado no Bambu Studio 02.08.02.60. É a linha de base. |
| `Jogos_Vorazes_otimizado_1peca.3mf` | **Imprima este primeiro** como teste de qualidade, ao lado de uma peça original. |
| `Jogos_Vorazes_otimizado_lote6.3mf` | **Recomendado para produção:** 6 peças por mesa (grade 3 × 2). |
| `Jogos_Vorazes_otimizado_lote9.3mf` | 9 peças por mesa (grade 3 × 3), para deixar imprimindo durante a noite. |
| `Jogos_Vorazes_opcional_lote6_camada020.3mf` | Opcional: igual ao lote de 6, mas com camada de 0,20 mm. Altera a superfície (veja os riscos). |
| `ferramentas/` | Scripts usados na análise, no fatiamento e na validação (veja o fim deste arquivo). |

Os 3MF otimizados são **cópias do original** com edições pontuais. A malha não muda, e o perfil, o filamento e a impressora continuam os mesmos. Abra no Bambu Studio 2.08, fatie e envie.

## O que mudou (só configurações internas)

| Configuração | Original | Otimizado | Afeta a superfície? |
|---|---|---|---|
| Padrão do preenchimento esparso (`sparse_infill_pattern`) | gyroid 15% | **lightning** 15% | Não. O preenchimento só sustenta os topos por dentro. |
| Aceleração da parede interna (`inner_wall_acceleration`) | 4000 (padrão) | **6000** | Não, a parede externa continua a 2000. |
| Aceleração do preenchimento esparso (`sparse_infill_acceleration`) | 100% (4000) | **150% (6000)** | Não. |
| Peças por mesa | 1 | **6** (ou 9) | Não. Cada camada de cada peça passa a ter mais tempo para esfriar. |

**Não mudou:** altura de camada de 0,16 mm, parede externa (60 mm/s, 2000 mm/s², largura 0,42), superfície de topo, saliências, pontes, suportes (árvore automática, 25°), costura aleatória, temperaturas, ventilação, fluxo, retração e z-hop.

Confirmei isso no G-code gerado. Comprimento extrudado por peça, original → otimizado:

| Tipo | Original | Otimizado |
|---|---|---|
| Parede externa | 30,481 m | 30,481 m |
| Parede interna | 28,208 m | 28,208 m |
| Superfície de topo / saliências / pontes | 0,152 / 0,231 / 0,234 m | 0,152 / 0,231 / 0,242 m |
| Suporte / interface | 17,600 / 0,137 m | 17,600 / 0,137 m |
| **Preenchimento esparso** | **25,121 m** | **1,570 m** |

## Tempos estimados

### Linha de base real
O G-code enviado foi fatiado no Bambu Studio **02.08.02.60**: **1h27m11s no total** (1h20m38s de modelo + cerca de 6,5 min de preparo), 400 camadas e 9,44 g. Ele corresponde exatamente ao 3MF enviado. A única diferença é a torre de purga, que o fatiador desliga sozinho com um filamento só.

### Comparação (motor do Bambu Studio)
Estes números são do estimador do próprio Bambu Studio, rodando no motor 02.04.00.70 (veja "Como foi medido"). Com as configurações originais, o 2.04 dá 1h31m57s contra 1h27m11s do 2.08, cerca de 3% a mais no tempo de modelo, com o mesmo peso. Por isso, a última coluna aplica a mesma proporção sobre a linha de base do 2.08.

| Mesa | Total da mesa | Por peça | Variação por peça | Por peça, convertido para 2.08 | g/peça |
|---|---|---|---|---|---|
| Original, 1 peça | 1h31m57s | 92,0 min | — | **87 min** (real do 2.08) | 9,43 |
| Otimizado, 1 peça | 1h24m20s | 84,3 min | −8% | ~80 min | 7,53 |
| Original, 6 peças (só lote) | 6h56m05s | 69,3 min | −25% | ~66 min | 9,38 |
| **Otimizado, 6 peças** | **5h57m34s** | **59,6 min** | **−35%** | **~57 min** | 7,48 |
| Otimizado, 9 peças | 8h49m03s | 58,8 min | −36% | ~56 min | 7,47 |
| Opcional: 6 peças, 0,20 mm | 5h07m23s | 51,2 min | −44% | ~49 min | 7,56 |

Lote só com as configurações originais, por peça: 4 → 71,4 min, 6 → 69,3, 9 → 68,5, 12 → 67,7. Acima de 6 peças o ganho por peça é pequeno, e o risco de perder a mesa inteira aumenta.

### Faixa de incerteza (estimativa independente)
Também escrevi um estimador cinemático próprio (`ferramentas/gstats.py`): planejador com jerk clássico de 9 mm/s e acelerações por `M204`. Ele fica a 7% do Bambu Studio na peça única, mas reage **menos** à velocidade programada. Pela leitura do código-fonte (`GCodeProcessor.cpp`), o estimador da Bambu não limita a velocidade de junção pela velocidade programada.

Nesse modelo mais conservador:

- Otimizado, 1 peça: −12% no tempo de modelo.
- Lote de 6 otimizado: cerca de **−19% por peça**, contando o preparo dividido por 6. O ganho vem quase só da diluição do preparo e das configurações internas.

**Conclusão honesta:** o ganho real do lote de 6 otimizado deve ficar **entre −19% e −35% por peça**, ou seja, entre ~57 e ~71 min por peça contra 87 min hoje. Só uma impressão real fecha esse número. A impressora mostra o tempo real no fim.

## Onde o tempo vai (peça única, G-code original 2.08)

Estimador próprio, sem os blocos condicionais de timelapse:

| Tipo | min | % | Velocidade média real |
|---|---|---|---|
| Parede externa | 23,7 | 31% | ~21 mm/s (programada a 60) |
| Parede interna | 13,0 | 17% | ~36 mm/s (limitada a 113 pelo fluxo de 7,5 mm³/s) |
| Preenchimento esparso | 9,8 | 13% | ~43 mm/s |
| Deslocamentos + wipe + retração | 13,6 | 18% | 3.549 retrações/z-hops |
| Casca vertical flutuante | 6,0 | 8% | |
| Suporte | 5,4 | 7% | |

- **A peça é limitada por aceleração, não por velocidade.** As escamas e a malha densa geram segmentos curtíssimos e cheios de curvas. A parede externa, programada a 60 mm/s, anda em média a ~21 mm/s. Por isso, subir as velocidades quase não ajudaria e ainda arriscaria o brilho do Silk. A parede externa ficou intocada.
- A redução de velocidade para resfriar camadas pequenas (`slow_down_layer_time` = 8 s) custa pouco na peça única: ~4,7 min. Em lote ela desaparece.
- Testei e **não** adotei:
  - "Evitar cruzar paredes" (+0,4% de tempo).
  - Desligar a casca vertical flutuante (+0,1%, nenhum ganho, e ela protege a superfície).
  - Gyroid ou grid a 10% com combinação de preenchimento (−6%; o lightning dá −8% e gasta menos material).
  - Camada de 0,20 mm (−17%, mas altera a superfície; ficou como opcional).

## Ganho sem risco algum: timelapse desligado
Cada camada tem um bloco condicional de timelapse (`M622 J1 … M623`): a cabeça vai até X0/X−48, para 0,3 s e volta. **Se o timelapse estiver ligado na janela de envio**, isso soma ~13 min de movimento e ~2 min de pausas **por mesa** (400 camadas), e esse tempo não entra na estimativa do Bambu Studio. Se a sua impressão real levou ~1,5 h contra a estimativa de 1h27m, essa é uma causa provável. Desligue o "Timelapse" ao enviar.

## Riscos para a qualidade

| Mudança | Risco | Mitigação |
|---|---|---|
| Preenchimento lightning | (1) Peça mais leve (7,5 g contra 9,4 g) e menos rígida por dentro. (2) Possível leve "pillowing" (afundamento) no topo das cabeças, porque o topo apoia numa estrutura mais esparsa. | Paredes e 6 camadas de topo (1 mm) continuam iguais. Se aparecer defeito no topo, volte para gyroid 10% + `infill_combination` (−6% em vez de −8%). |
| Aceleração interna 6000 | Muito baixo. 6000 é a aceleração padrão dos perfis oficiais "0.20mm Standard" e "0.16mm Optimal" da A1, que além disso usam 5000 na parede externa. Aqui a parede externa continua a 2000. | Compare as escamas da peça de teste com a original, procurando ondulação (ringing). |
| Lote de 6/9 | (1) Mais deslocamentos entre peças, o que pode gerar fiapos (o Silk "fia" com facilidade). (2) Se uma peça se soltar, pode derrubar as vizinhas. (3) O nivelamento automático cobre área maior (~110 × 143 mm) e leva alguns minutos a mais, que não entram na estimativa. | A folga entre peças no 1º camada é ≥ 6 mm. Mantenha a placa texturizada limpa (lave com água e detergente). Acompanhe a 1ª camada. |
| Opcional 0,20 mm | Degraus mais visíveis nas escamas, no bico, nas presas e nos topos curvos. O Silk realça linhas de camada. | Só use se o teste comparativo aprovar. |

**Efeito positivo do lote:** cada peça ganha ~6–9× mais tempo entre camadas. Isso tende a **melhorar** pontas finas (bico, presas, crista), que esquentam demais na peça única.

## Testes necessários antes de produzir

1. **Abra `Jogos_Vorazes_otimizado_lote6.3mf` no seu Bambu Studio 2.08 e fatie.** Confira:
   - a estimativa, que deve ficar perto de ~5h40m–6h (o 2.08 tende a dar ~3–5% menos que o 2.04);
   - na pré-visualização, que suportes, paredes e topos aparecem como no original;
   - que as 6 peças estão separadas.
2. **Peça de teste:** imprima `Jogos_Vorazes_otimizado_1peca.3mf` e compare lado a lado com uma peça original. Verifique:
   - brilho e uniformidade da cor;
   - definição das escamas e dos relevos;
   - topo das cabeças, procurando afundamento;
   - costura;
   - rigidez ao apertar levemente.
3. **Primeiro lote de 6:**
   - acompanhe a 1ª camada das 6 peças;
   - veja se aparecem fiapos entre elas;
   - anote o **tempo real** que a impressora mostra no fim e divida por 6. Esse número substitui as estimativas acima.
4. Só depois disso, se quiser, teste o lote de 9 ou a variante de 0,20 mm.

Os 3MF dos lotes ainda mostram a miniatura antiga, com 1 peça. Ela é atualizada quando você fatia e salva no Bambu Studio.

## Como foi medido (reprodutível)

- **O que havia no ambiente:** só o projeto anterior (porta-ampola). Não havia código-fonte, binário, scripts nem logs do Bambu Studio de sessões anteriores. Por isso a análise foi montada do zero, seguindo o mesmo método do porta-ampola (original preservado, cópia editada, comparação documentada).
- **Fatiador usado:** Bambu Studio **02.04.00.70**, o AppImage oficial do GitHub, em modo linha de comando. Foi a versão mais nova cujo binário Linux consegui localizar. Os assets da 02.08.x usam outro nome de arquivo e não consegui encontrá-los. **Nada foi compilado.** Só foi preciso uma biblioteca vazia no lugar do WebKit (`ferramentas/webkit_stub.c`), que o modo linha de comando não usa.
- **Por que o 2.04 serve para comparar:** com o 3MF original, ele chegou ao mesmo peso (9,43 g contra 9,44 g), às mesmas 400 camadas e ao mesmo comprimento de cada tipo de extrusão que o 2.08. A diferença está nas retrações (6.593 contra 3.549, porque o 2.08 elimina mais retrações). Algumas opções novas do 2.08 são ignoradas pelo 2.04. Por isso o entregável é o **3MF**, para você fatiar no 2.08, e **não** um G-code gerado aqui.
- **G-code não foi editado à mão.** Não foi necessário: todas as mudanças são configurações do fatiador, e assim os comandos específicos da Bambu (`M73`, `M991`, `M622/M623`, `M624/M625`, `G29`, start/end) saem do próprio fatiador.
- **Validação:** `ferramentas/validate.py` verificou nos G-codes gerados:
  - start e end G-code com a mesma sequência de comandos do original (só mudam `M73` e a área do `G29`);
  - blocos condicionais e de exclusão de objetos balanceados;
  - `M73 L` sequencial e `M73 P` até 100%;
  - camadas iguais ao cabeçalho;
  - extrusões dentro da mesa e objetos sem sobreposição.

  Resultado: **aprovado** para 1, 6 e 9 peças e para a variante de 0,20 mm.

### Ferramentas
- `bs.sh`: atalho para rodar o Bambu Studio 2.04 em modo linha de comando (AppImage extraído + biblioteca vazia no lugar do WebKit).
- `variant.py`: copia um 3MF aplicando ajustes em `project_settings.config`, fatia e resume os tempos.
- `batch3mf.py`: cria um 3MF com N instâncias em grade (espaçamento usado: 38 × 76 mm).
- `gstats.py`: tempo por tipo de extrusão e por camada, retrações e z-hops (estimador independente).
- `coolloss.py`: estima o tempo perdido com a redução de velocidade.
- `cfgdiff.py`: compara a configuração do G-code com a do 3MF.
- `validate.py`: validação de integridade.
- `ajustes_*.json`: os ajustes aplicados.
