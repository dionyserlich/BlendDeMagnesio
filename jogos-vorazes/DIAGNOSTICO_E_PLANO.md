# Jogos Vorazes (anel tordo × cobra): diagnóstico e plano de otimização

Impressora: Bambu Lab A1, bico 0,4 mm. Filamento: PLA Silk dourado Masterprint.
Esta é a **primeira entrega (Fase 1)**: diagnóstico e plano. Nenhuma configuração foi alterada e nenhum G-code foi modificado.

## Resumo

1. **O 3MF é um projeto editável.** Tem a malha, as configurações e as miniaturas, mas nenhum G-code dentro. A otimização pode ser feita só nas configurações do Bambu Studio. **Não é preciso compilar nem escrever um motor de fatiamento.**
2. **O G-code enviado corresponde a este 3MF.** É a mesma malha e a mesma configuração. Só a posição na mesa muda: a peça está 10 mm deslocada em X. A distância mediana entre a parede externa e o contorno da malha é de 0,210 mm, exatamente meia largura de linha; 99 % dos pontos ficam a menos de 0,45 mm.
3. **Para onde vão as 1h27m11s estimadas pelo Bambu Studio:**
   - preparação da impressora: 6m33s;
   - **timelapse: cerca de 12m50s.** O Bambu soma esse tempo, mas a impressora só executa esses movimentos se o timelapse estiver ligado no envio;
   - impressão das camadas: cerca de 1h08m.
4. **A peça é pequena para o tempo mínimo de camada (8 s) do perfil de PLA Silk.** 345 das 400 camadas são desaceleradas. Isso tem duas consequências:
   - aumentar velocidade ou aceleração numa peça sozinha quase não reduz o tempo;
   - a **parede externa varia entre 20 e 60 mm/s conforme a altura**. Isso é um risco direto para o brilho uniforme do silk. A variação se concentra em duas faixas: 16–28 mm e 44–64 mm, a região das cabeças.
5. **O maior ganho comercial vem de imprimir várias peças por mesa.** Com timelapse desligado e 3 a 6 peças por mesa, a projeção é de **−22% a −24% por peça**. Somando aceleração 6000 nas linhas internas, chega a **cerca de −27% por peça** (1h28m → 1h04m). Além disso, a parede externa passa a sair sempre a 60 mm/s, o que deixa o brilho mais uniforme.
6. **Há perda de detalhe nas pontas das presas.** Perto do topo, entre 56 e 64 mm de altura, há seções isoladas minúsculas (0,01 a 0,4 mm², ou seja, ~0,1 a 0,7 mm de largura) que o G-code não imprime em todas as camadas. *Correção feita depois do re-fatiamento (Etapa B):* o gerador Arachne **não** resolve isso. Os dois geradores deixam de imprimir cerca de 1/4 dessas ilhas, em camadas diferentes (seção 4.5).

## 1. Arquivos e preservação

| Arquivo | Conteúdo | SHA-256 |
|---|---|---|
| `original/Jogos_Vorazes_malha_suavizada-02.3mf` | Projeto Bambu Studio 02.08.02.60: 1 objeto, 976.150 triângulos, configurações e miniaturas. Sem G-code fatiado. | `79af27a33a84799d…` |
| `original/Jogos_Vorazes_furos_1-03mm_PLA_1h27m.gcode` | G-code fatiado do mesmo projeto (400 camadas, 9,44 g) | `a610b8dd8852d138…` |

- As cópias estão em `original/`, com permissão só de leitura. As somas completas estão em `original/SHA256SUMS`. Para conferir: `cd original && sha256sum -c SHA256SUMS`.
- Toda variante futura será um arquivo novo. Os originais nunca serão sobrescritos.
- O nome do G-code fala em "furos", mas a comparação camada a camada não mostra diferença de geometria em relação ao 3MF "malha_suavizada-02". Veja `analise/comparacao_gcode_malha.txt`.

**A peça.** O anel fica em pé na mesa e mede 19,0 × 64,2 × 64,05 mm (X × Y × Z). O volume sólido é de 13,4 cm³. A malha é fechada, sem arestas abertas e com uma única peça. A área apoiada na mesa é de só 8,3 mm²; o resto da base fica nos suportes em árvore. Há 653 mm² de faces voltadas para baixo inclinadas mais de 45° em relação à vertical, dos quais 267 mm² são quase horizontais (mais de 60°). São as faces de baixo do anel e das cabeças, que pedem suporte.

## 2. Configuração atual

O projeto usa os perfis de sistema "0.16mm High Quality @BBL A1" e "Generic PLA Silk @BBL A1". Só duas coisas foram alteradas em relação ao sistema: o suporte foi ligado e a costura está em "aleatória". Os valores abaixo foram conferidos contra os perfis oficiais do Bambu Studio no GitHub.

| Área | Valor atual | Observação |
|---|---|---|
| Camada | 0,16 mm (1ª camada 0,20) → 400 camadas | Perfil de alta qualidade |
| Paredes | 2 voltas, gerador **Clássico**, `detect_thin_wall` desligado | Deixa de imprimir parte das pontas das presas, assim como o Arachne (seção 4.5) |
| Topo/base | 6 / 4 camadas; `ensure_vertical_shell_thickness` = enabled | Gera o "Floating vertical shell" (5 min) |
| Preenchimento | Gyroid 15 %, sem combinar camadas | |
| Suporte | Árvore (auto), ângulo 25°, também apoiado sobre o modelo | 7 % do tempo; concentrado em 0–8 mm e 48–56 mm |
| Velocidades | parede externa 60 · interna 150 · preenchimento 200 · sólido 200 · topo 150 · deslocamento 700 mm/s | Na prática, as linhas internas ficam limitadas pelo fluxo (abaixo) |
| Acelerações | padrão 4000 · parede externa 2000 · topo 2000 · deslocamento 10000 · 1ª camada 500 mm/s² | Os perfis Standard/Optimal do A1 usam padrão 6000 |
| Fluxo máximo | 7,5 mm³/s (limita as paredes internas a ~113 mm/s e o preenchimento a ~113 mm/s) | |
| Temperatura | bico 220 °C · mesa 55 °C (PEI texturizada) | Dentro da faixa divulgada para o Masterprint Silk |
| Resfriamento | ventoinha 60–80 %; **tempo mínimo de camada 8 s**; velocidade mínima 20 mm/s; lógica `uniform_cooling` | Determina o ritmo da peça (seção 4.2) |
| Deslocamentos | retração 0,5 mm (valor do perfil do filamento, que substitui os 0,8 mm da impressora); wipe 2 mm; z-hop 0,4 mm em espiral ("Auto Lift"); evitar cruzar paredes desligado | |
| Costura | aleatória | Escolha do usuário; mantida |

## 3. Para onde vai o tempo

A estimativa foi refeita movimento a movimento com `ferramentas/analisar_gcode.py`. O planejador reimplementa o modelo de movimento do estimador do Bambu Studio. O resultado ficou **0,5 % acima** do tempo do modelo informado pelo Bambu (1h21m04s contra 1h20m38s).

| Bloco | Tempo | Observação |
|---|---:|---|
| Preparação (aquecimento, nivelamento, limpeza, calibrações) | 6m33s | Diferença entre o total e o tempo do modelo no cabeçalho |
| **Timelapse (blocos condicionais)** | **12m52s** | Em cada camada a cabeça vai até X = −48 mm e volta. O firmware só executa se o timelapse estiver ligado no envio |
| Impressão das camadas | 1h08m11s | Detalhado abaixo |

A impressão das camadas (1h08m11s) se divide assim:

| Operação | Tempo | % | Sem a desaceleração de resfriamento |
|---|---:|---:|---:|
| Parede externa | 17m18s | 25,4 | 16m38s |
| Parede interna | 12m39s | 18,5 | 11m40s |
| Preenchimento esparso | 9m04s | 13,3 | 7m46s |
| Sólidos (floating vertical shell, sólido interno, gap fill, topo, ponte) | 7m55s | 11,6 | 7m29s |
| Suporte e interface | 4m51s | 7,1 | 4m07s |
| **Deslocamentos, z-hop, wipe e retração** | **16m01s** | **23,5** | 16m00s |
| Paredes em saliência | 0m23s | 0,6 | 0m23s |

- O tempo vem quase todo de movimentos curtos e de acelerações, não da velocidade máxima. São 94.671 arcos, a mediana de deslocamento é de 3,4 mm e há 8.902 deslocamentos por peça. O volume médio extrudado é de só ~2 mm³/s, contra um limite de 7,5.
- Deslocamentos somam 108 m por peça, com 1.771 z-hops em espiral e 3.549 retrações. Isso vem da geometria: o anel em pé gera duas "ilhas" por camada, uma de cada lado do anel, além das árvores de suporte.

## 4. Diagnóstico

### 4.1 Timelapse

O G-code traz, em toda camada, um bloco `SKIPPABLE` do tipo `timelapse`. Nele a cabeça vai a X = −48,2 mm, sendo 48 mm desse trajeto a 50 mm/s, e espera 0,3 s. A execução depende de `M1002 judge_flag timelapse_record_flag`, ou seja, da opção marcada no envio.

O estimador do Bambu soma esse tempo no total. O código-fonte (`GCodeProcessor.cpp`) contabiliza esse tempo à parte, em `skippable_part_time`, mas inclui no total. Os números confirmam: só dá para reproduzir as 1h20m38s incluindo esses blocos.

**Se o timelapse estiver ligado:** desligar economiza ~13 min por mesa sem nenhum efeito visual.
**Se já estiver desligado:** a impressão real já dura ~1h15m, e o "1h27m" do nome do arquivo é pessimista. *(Preciso confirmar com você qual é o caso.)*

### 4.2 Tempo mínimo de camada e brilho

O Bambu Studio 2.08 calcula o tempo de cada camada como comprimento ÷ velocidade, sem aceleração e incluindo o bloco de timelapse. Quando a soma fica abaixo de 8 s, ele iguala todas as linhas mais rápidas a uma velocidade v\*, incluindo a parede externa (`GCodeEditor.cpp` e `CoolingBuffer.cpp`, tag v02.08.02.60). Nesta peça:

- 345 de 400 camadas têm paredes internas ou preenchimento desacelerados;
- **225 camadas têm a parede externa abaixo de 60 mm/s.**

Velocidade predominante da parede externa por altura:

| Altura (mm) | 0–12 | 12–16 | 16–28 | 28–44 | 44–48 | 48–52 | 52–56 | 56–64 |
|---|---|---|---|---|---|---|---|---|
| mm/s (mediana) | 60 | 56 | 43–47 | 60 | 43 | 31 | 23 | 36–37 |

O PLA silk muda de brilho e tom conforme a velocidade e o resfriamento. Essa variação pode aparecer como **faixas horizontais**, justamente na região das cabeças. Isso deve ser conferido nas peças já impressas.

Há duas formas de corrigir:
- **Várias peças por mesa.** Cada camada passa a durar mais de 8 s e a desaceleração desaparece.
- **Lógica `consistent_surface`.** Para pedidos de uma peça só, o Bambu Studio 2.08 tem uma opção, visível só no modo desenvolvedor, que desacelera primeiro preenchimento e paredes internas. A descrição oficial: *"preserving external perimeter speed for better surface finish on glossy filaments… maintains consistent surface shine"*.

Como a camada já está "presa" nos 8 s, **qualquer aumento de velocidade numa peça sozinha é absorvido pela desaceleração.** Por isso a otimização começa pelo número de peças por mesa.

### 4.3 Deslocamentos

Os deslocamentos, z-hop, wipe e retração (23,5 %) vêm em grande parte da geometria. Reduzir z-hop ou wipe economiza pouco (1–3 min) e arrisca riscar ou deixar fios na superfície brilhante. Fica em baixa prioridade.

### 4.4 Velocidade e fluxo

Projeção com 4 peças por mesa:

| Mudança | Ganho por peça |
|---|---|
| Fluxo máximo de 7,5 para 10 mm³/s (já com aceleração 6000) | −0,5 min |
| Aceleração da parede externa de 2000 para 3000 (já com aceleração 6000) | −1,4 min |
| Aceleração padrão de 4000 para 6000 (paredes internas, preenchimento, suporte) | −3,7 min |

As duas primeiras mudanças afetam diretamente o acabamento e quase não rendem. **Não recomendo.** A terceira afeta só linhas escondidas e vale a pena.

### 4.5 Detalhes perdidos

O script `ferramentas/comparar_gcode_malha.py` corta a malha em cada camada amostrada e procura trechos do contorno sem nenhuma extrusão a menos de 1 mm.

O resultado: trechos sem extrusão entre **Z 55,9 e 63,9 mm**, na região X 119,7–122,4 / Y 128–136 (coordenadas do 3MF). Com `--ilhas`, o script mostra o que são: seções isoladas da malha com 0,01 a 0,4 mm² de área, ou seja, as pontas das presas da cobra. São duas ilhas lado a lado, perto de X 120,5 e 122,2 / Y 134. Uma ponta afina para baixo até Z ≈ 56,7; a outra começa em Z ≈ 58,8 e engrossa até se juntar à mandíbula, perto de Z 61.

*Correção feita depois do re-fatiamento (Etapa B).* A primeira versão desta seção dizia que o Arachne imprimiria essas pontas. O G-code real do Arachne mostra que não. Das 131 ilhas pequenas (até 2 mm²) nas 400 camadas:

| Gerador | Ilhas não impressas | Soma das áreas não impressas |
|---|---:|---:|
| Clássico (original) | 33 | 3,40 mm² × camada |
| Arachne | 32 | 4,16 mm² × camada |

- Os dois perdem ilhas, mas em camadas diferentes. O Clássico imprime a ponta de cima entre Z 59,9 e 61,0 como pequenos laços; o Arachne não imprime nada ali (conferido direto no G-code em Z 60,68).
- O Arachne, por sua vez, imprime trechos em Z 55,9–56,4, 59,1–59,7 e 63,1 que o Clássico perdia.
- Ilhas com menos de ~0,5 mm de largura ficam no limite do que um bico de 0,4 mm consegue fazer, com qualquer gerador. Para imprimi-las sempre, seria preciso engrossar as presas no modelo ou usar um bico menor. As duas opções mudam o produto ou o tempo e não foram aplicadas.
- O critério final é a comparação física das presas: peça T0 (Clássico) contra o teste de 4 peças (Arachne).

### 4.6 Suportes

Os suportes ocupam 4m51s (7 %). Ficam na base (21 % do tempo da faixa de 0–8 mm) e sob o arco interno e as cabeças (10 % na faixa de 48–56 mm). Mexer nos suportes economiza pouco e pode piorar a face de baixo das cabeças ou deixar marcas. Fica em baixa prioridade, só com teste.

### 4.7 Filamento: PLA Silk dourado Masterprint

Não encontrei ficha técnica oficial do PLA Silk dourado. Anúncios de lojas da linha Silk da Masterprint indicam:
- bico de 190–230 °C, recomendado 210–220 °C;
- mesa de 40–60 °C.

O PLA comum da marca anuncia até 25 mm³/s. O projeto usa 220 °C e 55 °C, dentro da faixa. O limite de 7,5 mm³/s do perfil genérico é conservador, mas aumentá-lo não traz ganho (seção 4.4).

Recomendação: criar um perfil de usuário "Masterprint PLA Silk Dourado" com base no "Generic PLA Silk @BBL A1", mantendo temperatura, fluxo e resfriamento, e calibrar uma vez a razão de fluxo e o K (Flow Dynamics). A cor salva no projeto é cinza (#A4AAAC); isso só afeta a visualização.

## 5. Oportunidades classificadas

O ganho por peça é contado a partir do original (1h27m–1h28m) e vem do simulador `ferramentas/projetar_cenarios.py`. Os itens marcados "re-fatiar" só podem ser medidos depois de fatiar de novo no Bambu Studio; o número indicado é uma estimativa grosseira.

| # | Oportunidade | Ganho estimado por peça | Risco visual | Dificuldade de validação |
|---|---|---|---|---|
| 1 | **Timelapse desligado na produção** (opção no envio) | **−12,9 min (−15 %)**, se hoje está ligado | Nenhum | Muito baixa: cronometrar |
| 2 | **3 a 6 peças por mesa**, impressão por camada | **−7 a −8 min a mais**: total de −22 % a −24 % contra o original; 1h07–1h08 por peça | Baixo–médio. A parede externa fica a 60 mm/s constante, com brilho mais uniforme, mas diferente das peças atuais nas faixas lentas. Há mais deslocamentos entre peças, com risco de fio | Média: uma mesa de teste |
| 3 | **Aceleração padrão 4000 → 6000** (a parede externa e o topo ficam em 2000) | −3,7 min (−4 %) com várias peças; ~0 com uma peça | Baixo (linhas escondidas) | Média |
| 4 | **Gerador Arachne** (paredes) | ~0. Medido: sem efeito claro no tempo | Neutro. Elimina o gap fill atrás da parede externa (459 → 27 mm por peça), mas **não** recupera as pontas das presas (seção 4.5) | Média: script de comparação + lupa |
| 5 | `consistent_surface`, só se imprimir uma peça | +0,7 min (+1 %) | **Melhora**: parede externa a 60 mm/s em 81 % do comprimento, contra 37 % hoje | Média |
| 6 | Preenchimento: combinar a cada 2 camadas e 10–12 % | −2 a −4 min (re-fatiar; só ajuda com várias peças) | Baixo | Baixa–média |
| 7a | Camada de 0,20 mm na peça inteira | −15 % a −20 % (re-fatiar) | **Alto**: o silk realça linhas de camada nas encostas e no topo, e há perda de resolução vertical nas escamas e penas | Alta: A/B lado a lado |
| 7b | Camada de 0,20 mm só no meio (≈ 8–44 mm), 0,16 nas pontas | −6 % a −10 % (re-fatiar) | Médio: a troca de altura pode marcar uma faixa no brilho | Alta |
| 8 | `ensure_vertical_shell_thickness` = partial | −1 a −3 min (re-fatiar) | Médio: o preenchimento pode transparecer nas encostas | Média |
| 9 | Suportes (estilo, ângulo, interface) | −1 a −2 min (re-fatiar) | Médio–alto: marcas sob as cabeças e no arco interno | Alta |
| 10 | Deslocamentos (z-hop, wipe, evitar cruzar paredes) | −1 a −3 min, incerto | Médio: riscos e fios | Média |
| 11 | Calibração de fluxo dinâmica desligada, com o K já salvo | ~−1 min por mesa | Baixo | Baixa |

**Não recomendados:**
- aumentar a velocidade ou a aceleração da parede externa;
- aumentar o fluxo máximo;
- reduzir o tempo mínimo de camada para 5 s (−4,5 min numa peça sozinha, com risco nas cabeças; desnecessário com várias peças);
- deitar o anel: corta camadas, mas exige suporte sob toda a face de baixo, deixando marcas no silk;
- editar o G-code já fatiado.

**Tempo por mesa** (timelapse desligado, aceleração atual):

| Peças por mesa | Tempo da mesa | Por peça |
|---:|---:|---:|
| 2 | 2h18m | 1h09m |
| 3 | 3h24m | 1h08m |
| 4 | 4h31m (4h16m com aceleração 6000) | 1h08m (1h04m) |
| 6 | 6h44m | 1h07m |
| 8 | 8h58m | 1h07m |

A pegada de cada peça com suportes é de ~26 × 66 mm. A mesa de 256 × 256 mm comporta bem mais de 8. O limite prático é o risco: se uma peça descolar, a mesa inteira se perde. Isso pesa porque a área de contato com a mesa é de só 8 mm².

## 6. Plano priorizado (Fases 2 a 4)

**Arquitetura: sem motor próprio e sem compilação.**
- Todas as alavancas acima são opções do próprio Bambu Studio 2.08.02.60 ou do envio da impressão.
- Opções que só aparecem no modo desenvolvedor, como `cooling_slowdown_logic`, podem ser gravadas diretamente na configuração do projeto. Ela é um JSON dentro do 3MF.
- Quem fatia é sempre o Bambu Studio oficial. Assim, os comandos próprios do A1 continuam corretos: blocos `M622/M623`, `M73`, calibrações.
- Neste ambiente, os domínios da Bambu Lab e as releases do GitHub estão bloqueados. Por isso o fatiamento é feito no seu Bambu Studio, na mesma versão do arquivo, e a validação é feita aqui com os scripts.
- **Não há motivo para pós-processar G-code.** Nenhuma alavanca exige isso, e editar o G-code fatiado contornaria a lógica de resfriamento e as estimativas da impressora.

### Etapa A: sem re-fatiar (imediato)
1. Confirmar se o timelapse está sendo usado. Para produção, desligar no envio.
2. Imprimir uma peça com o G-code original e timelapse desligado. Isso mede o tempo real de referência (~1h15m projetado) e serve de amostra T0 para comparar o brilho.

### Etapa B: perfil "Produção A" (re-fatiar)
1. Gerar um 3MF novo a partir do original, sem mexer na malha, com estas mudanças:
   - 4 instâncias organizadas;
   - `default_acceleration` = 6000;
   - `wall_generator` = arachne.
2. Para pedidos de uma peça só, gerar uma variante "1 peça" com `cooling_slowdown_logic` = `consistent_surface`.
3. Você fatia no Bambu Studio e me devolve o G-code ou o 3MF fatiado.
4. Eu rodo `analisar_gcode.py`, `projetar_cenarios.py` e `comparar_gcode_malha.py` e comparo com o original:
   - tempo;
   - velocidade da parede externa por altura;
   - ilhas pequenas (pontas das presas) impressas ou não, com `--ilhas`;
   - nenhum comando de máquina alterado.

### Etapa C: ganhos adicionais, só se a Etapa B for aprovada visualmente
- Preenchimento (item 6) e cascas verticais (item 8): risco baixo a médio.
- Camada variável (item 7b) e depois 0,20 mm (item 7a), sempre em A/B.

## 7. Validação (Fase 4)

**Tempo.** Para cada variante vou comparar três valores:
- a estimativa do Bambu, no cabeçalho do G-code;
- a estimativa deste script, que separa o timelapse condicional;
- o **tempo real cronometrado** do início ao fim da mesa, com aquecimento.

Limitações da estimativa:
- o firmware do A1 não segue exatamente o planejador do estimador (arcos, junções, compensação de vibração);
- o tempo de aquecimento varia com o ambiente;
- os blocos condicionais mudam o total conforme as opções do envio.

Considero aceitável uma diferença de até ±5 % entre o projetado e o medido.

**Impressão de teste representativa.** Uma mesa da "Produção A" com 4 peças, timelapse desligado, ~4h20m. Ela será comparada com a peça T0 da Etapa A, feita com o mesmo rolo, a mesma impressora e a mesma placa. As 4 peças ficam em fila ao longo de X, como na produção (veja `ETAPA_B.md`). O teste compara posições da esquerda para a direita e a primeira e a última peça na ordem de impressão de cada camada.

**Critérios de aceitação** (a peça nova deve ficar igual ou melhor que a T0 em todos):

| Critério | Como avaliar |
|---|---|
| Brilho uniforme | Fotos com uma única luz a 45° e câmera fixa, girando a peça em 4 posições de 90°. Não pode haver faixa horizontal de brilho ou tom, principalmente em 16–28 mm e 44–64 mm. As 4 peças da mesa devem ter o mesmo tom. |
| Detalhes | Pontas das presas (Z 56–64 mm) iguais ou melhores que na T0, vistas com lupa. Escamas e penas nítidas, sem bolhas. `comparar_gcode_malha.py --ilhas` sem mais ilhas perdidas que o original. |
| Dimensões | Paquímetro: altura 64,05 mm, Y 64,2 mm, X 19,0 mm, todos com tolerância de ±0,2 mm, e iguais à T0. |
| Defeitos | Fios entre as peças, pontos da costura, marcas de suporte no arco interno e sob as cabeças (nota de 0 a 3), pé de elefante, deslocamento de camada, subextrusão, queda nas saliências. |
| Tempo | Tempo real por peça no máximo 5 % acima do projetado. |

Só considero a otimização aprovada depois desse teste físico. Gerar o arquivo não basta.

## 8. Limitações desta análise

- Os ganhos das seções 4 e 5 são projeções sobre os caminhos já fatiados. Elas reaplicam a lógica de resfriamento do Bambu Studio e usam valores medidos de preparação (6m33s) e de deslocamento entre peças (0,4 s por troca; com 0,6 s, o ganho cai ~1 ponto). O valor final sai do re-fatiamento e do cronômetro.
- A preparação pode aumentar um pouco com mais peças, porque o nivelamento cobre a área ocupada.
- A wiki da Bambu Lab e a página do produto não puderam ser abertas daqui: a política de rede bloqueia esses domínios. O comportamento do fatiador foi conferido no código-fonte e nos perfis oficiais do Bambu Studio, na tag exata v02.08.02.60.
- Não existe ficha técnica oficial do PLA Silk dourado da Masterprint. Os dados do filamento vêm de anúncios de lojas e devem ser confirmados no rótulo do rolo.

## 9. Como reproduzir

Requisitos: Python 3 e numpy, só para os scripts da malha. Todos os scripts são somente leitura.

```bash
cd jogos-vorazes
python3 -I ferramentas/analisar_gcode.py original/Jogos_Vorazes_furos_1-03mm_PLA_1h27m.gcode --json analise/gcode_original.json
python3 -I ferramentas/analisar_malha_3mf.py original/Jogos_Vorazes_malha_suavizada-02.3mf --json analise/malha_3mf.json
python3 -I ferramentas/comparar_gcode_malha.py original/Jogos_Vorazes_malha_suavizada-02.3mf original/Jogos_Vorazes_furos_1-03mm_PLA_1h27m.gcode --passo 2
python3 -I ferramentas/projetar_cenarios.py original/Jogos_Vorazes_furos_1-03mm_PLA_1h27m.gcode --json analise/cenarios.json
```

As saídas desta análise estão em `analise/`.

## Fontes

- Bambu Studio, código-fonte e perfis oficiais na tag v02.08.02.60:
  - [CoolingBuffer.cpp](https://github.com/bambulab/BambuStudio/blob/v02.08.02.60/src/libslic3r/GCode/CoolingBuffer.cpp)
  - [GCodeEditor.cpp](https://github.com/bambulab/BambuStudio/blob/v02.08.02.60/src/libslic3r/GCode/GCodeEditor.cpp)
  - [GCodeProcessor.cpp](https://github.com/bambulab/BambuStudio/blob/v02.08.02.60/src/libslic3r/GCode/GCodeProcessor.cpp)
  - [PrintConfig.cpp](https://github.com/bambulab/BambuStudio/blob/v02.08.02.60/src/libslic3r/PrintConfig.cpp)
  - [perfis BBL (processo e filamento)](https://github.com/bambulab/BambuStudio/tree/master/resources/profiles/BBL)
- Bambu Lab Wiki: [Timelapse](https://wiki.bambulab.com/en/software/bambu-studio/Timelapse) (consultada só pelo resumo de busca; o acesso direto está bloqueado aqui).
- Fórum Bambu Lab:
  - [tempo mínimo de camada](https://forum.bambulab.com/t/bambu-studio-minimum-layer-time-setting/3742)
  - [timelapse tradicional no A1](https://forum.bambulab.com/t/timelapses-but-it-does-not-go-to-the-side-every-layer/155515)
  - [Flow Dynamics no A1](https://forum.bambulab.com/t/questions-about-flow-dynamics-and-extrusion-multiplier-on-the-a1/47642)
- Especificações do A1 (500 mm/s, 10.000 mm/s², 28 mm³/s): [folha de especificações](https://cdn.shopify.com/s/files/1/0635/8247/0318/files/A1_Spec_EN_1.pdf) e [página da loja](https://eu.store.bambulab.com/en-mt/products/a1), consultadas pelo resumo de busca. Os limites de máquina usados nos cálculos são os do perfil "Bambu Lab A1 0.4 nozzle" gravado no próprio G-code.
- Masterprint PLA Silk (dados de revendedores):
  - [3DPD](https://3dpd.com.br/produtos/filamento-pla-para-impressora-3d-silk-masterprint/)
  - [Mundoware](https://www.mundoware.com.br/filamento-de-impressora-3d-pla-silk-azul-masterprint)
  - [Tavares 3D Print](https://www.tavares3dprint.com.br/produtos/filamento-pla-silk-vermelho-1kg-master-print-1-75mm1/)
  - [Kabum, PLA comum Masterprint](https://www.kabum.com.br/produto/1022924/filamento-de-impressora-3d-pla-roxo-1-75mm-1kg-cor-brilhante-textura-macia-masterprint-filamento-3d)
