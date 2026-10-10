# Etapa B: arquivos para fatiar e imprimir

Os dois projetos ficam em `variantes/`. Foram gerados a partir do 3MF original por `ferramentas/gerar_variante_3mf.py`, que só altera as partes de texto do projeto:

- a malha é copiada byte a byte;
- o original continua intacto em `original/`;
- o formato segue o código-fonte do Bambu Studio 02.08.02.60 (exportador e leitor de 3MF);
- os dois arquivos foram conferidos por `ferramentas/conferir_variante_3mf.py`.

| Arquivo | Para quê | O que muda em relação ao original |
|---|---|---|
| `variantes/Jogos_Vorazes_producao_4pecas.3mf` | Produção em lote, e também a impressão de teste desta etapa | 4 cópias em linha ao longo de X, em X = 64, 109, 154 e 199 mm (Y = 128). Aceleração padrão 4000 → 6000. Gerador de paredes Clássico → Arachne. Resfriamento `consistent_surface` |
| `variantes/Jogos_Vorazes_1peca.3mf` | Pedidos de uma peça | Gerador de paredes Clássico → Arachne. Resfriamento `consistent_surface`. A posição e a aceleração ficam como no original |

## Por que cada mudança

- **4 cópias por mesa.** Cada camada passa a durar mais que o tempo mínimo de 8 s. Com isso, o fatiador para de desacelerar as camadas, e a parede externa sai a 60 mm/s em toda a altura, com brilho uniforme. A preparação e o timelapse também passam a ser divididos por 4.
  - As cópias ficam em linha ao longo de X, com a mesma orientação do original. A mesa (eixo Y) continua se movendo dentro de cada peça, mas, comparado a uma grade 2 × 2, a fila evita ~800 deslocamentos longos da mesa por impressão (~22 % menos). Isso importa porque as peças são altas e tocam a placa em só 8 mm².
  - Em cada camada, a ordem é da direita para a esquerda (X 199 → 154 → 109 → 64), com uma volta de ~135 mm à direita na troca de camada.
  - O Bambu Studio não confere a distância entre cópias do mesmo objeto. **Não gire nem mude a escala de uma cópia isolada**: ela vira um objeto separado, com suporte gerado à parte.
  - Espaçamento:
    - 45 mm entre os centros;
    - 26,0 mm entre as malhas (o "Organizar" do Bambu reserva 24 mm com suporte em árvore);
    - 18,2 mm entre as áreas de suporte.
  - A área de cada cópia, medida no G-code original e já com os suportes, é de 26,8 × 66,8 mm. O conjunto ocupa X 47–209 e Y 93–160, longe das bordas e da zona de detecção de bico enrolado (X ≥ 226, Y ≥ 224).
- **Aceleração padrão 6000.** Vale para parede interna, preenchimento, sólidos internos, gap fill, ponte e suporte. **Parede externa, saliências e topo continuam em 2000**, e a primeira camada continua em 500. 6000 é o valor dos perfis Standard e Optimal do A1.
- **Arachne.** Elimina o gap fill em zigue-zague atrás da parede externa (de 459 para 27 mm por peça) e reduz retrações e deslocamentos. **Não recupera as pontas das presas.** A expectativa inicial era essa, mas o fatiamento real mostrou que não (veja "Resultado do fatiamento" abaixo).
- **`consistent_surface`.** Só age em camadas mais curtas que 8 s. Nessas camadas, o fatiador desacelera primeiro todas as linhas que não são parede externa: paredes internas, preenchimento, suporte, gap fill e também o pouco de superfície de topo que esta peça tem (6 s no total), até no mínimo 20 mm/s. A parede externa só desacelera se isso não bastar. Os últimos 10 mm de cada trecho desacelerado voltam à velocidade normal.
  - Na versão de 4 peças isso quase nunca acontece.
  - Na de 1 peça, mantém a parede externa a 60 mm/s em ~81 % do comprimento (hoje são 37 %).
  - Essa opção só aparece no **modo desenvolvedor** do Bambu Studio, por isso foi gravada direto no projeto.

## Como fatiar e enviar

1. Abra o arquivo no **Bambu Studio 02.08.02.60**, a mesma versão do original, **como projeto**: Arquivo → Abrir projeto. Se arrastar o arquivo para uma placa que já tem algo, escolha "Abrir como projeto". "Importar só a geometria" ignora todas as configurações do arquivo.
   - Os perfis aparecem como modificados ("0.16mm High Quality @BBL A1" e "Generic PLA Silk @BBL A1"). Isso é o esperado.
   - **Não troque e não sincronize o perfil de filamento**, nem pelo "sincronizar com o AMS". Isso apaga o `consistent_surface`, que fica invisível fora do modo desenvolvedor.
   - Se aparecer a pergunta sobre alterações não salvas, escolha **manter**.
2. Na versão de 4 peças, **não use "Organizar" (Arrange)**. As posições já deixam espaço para os suportes, e o "Organizar" faria outro arranjo, possivelmente em grade, com a mesa se movendo entre as peças. A miniatura do arquivo ainda mostra 1 peça até você salvar o projeto; é só a imagem de prévia. Na lista de objetos, as cópias aparecem como "instâncias" de um único objeto. Por isso todas usam sempre as mesmas configurações; aqui isso é desejável. A interface do 02.08.02.60 não cria instâncias (o "Clonar" cria objetos separados), mas o leitor de 3MF carrega e fatia esse formato normalmente: é o mesmo que o próprio exportador grava para instâncias.
3. Fatie e confira o tempo estimado. Na versão de 4 peças, espero algo **perto de 4h30m**. Esse número inclui ~13 min de timelapse condicional que a impressora só executa se o timelapse estiver ligado.
4. Antes de enviar, confira no G-code (em "Exportar G-code" ou no `.gcode.3mf`) que o cabeçalho tem estas linhas:
   - `; wall_generator = arachne`
   - `; cooling_slowdown_logic = consistent_surface`
   - `; default_acceleration = 6000` (só na versão de 4 peças)

   Ainda vão aparecer blocos "Gap infill": eles vêm do padrão da superfície de topo, não das paredes. Isso não indica que o Arachne deixou de ser aplicado.

   Na versão de 4 peças, o G-code também deve ter:
   - uma linha `; model label id:` com 4 números diferentes;
   - um nivelamento `G29 A1 X47.09 Y93.33 I161.76 J66.78` (±0,01).
5. Na janela de envio:
   - **Timelapse desligado**;
   - nivelamento da mesa ligado;
   - calibração de fluxo dinâmica como você costuma usar.
6. **Me mande o G-code fatiado** (ou o `.gcode.3mf`) antes de imprimir, se possível. Vou rodar:
   - `analisar_gcode.py`: tempo e velocidade da parede externa por altura;
   - `comparar_gcode_malha.py --ilhas`: quais pontas das presas são impressas;
   - `projetar_cenarios.py`.

   Com isso confiro se o ganho previsto se confirma e se nada inesperado mudou.

## Teste de impressão e critérios

Imprima uma mesa com as 4 peças e compare com a peça que você já tem, impressa com o G-code original. Use o mesmo rolo e a mesma placa. As 4 peças ficam na mesma faixa de Y. Então o teste compara posições da esquerda para a direita e a ordem de impressão em cada camada (a primeira peça, em X 199, e a última, em X 64), não frente contra fundo da mesa. Tempo projetado: **~4h16m de impressão real** (~1h04m por peça), contra ~1h15m por peça hoje sem timelapse. É uma projeção sobre os caminhos antigos; o Arachne pode mudar um pouco esse número.

| Critério | Como avaliar | Aprovado se |
|---|---|---|
| Brilho | Uma luz só, a 45°, câmera fixa, peça girada em 4 posições | Sem faixas horizontais, principalmente em 16–28 mm e 44–64 mm. As 4 peças com o mesmo tom. Igual ou melhor que a peça de referência |
| Detalhes | Lupa nas cabeças, escamas e penas | Pontas das presas iguais ou melhores que na peça de referência (Clássico). Escamas nítidas, sem bolhas. Se as presas ficarem piores, volte o gerador de paredes para Clássico (Qualidade → Gerador de paredes) |
| Dimensões | Paquímetro | Altura 64,05 mm, Y 64,2 mm, X 19,0 mm, todos ±0,2 mm, e iguais à peça de referência |
| Defeitos | Inspeção | Sem fios entre as peças, sem marcas novas de suporte, sem queda nas saliências, sem pé de elefante e sem deslocamento de camada |
| Tempo | Cronômetro, do início ao fim da mesa | No máximo ~5 % acima de 4h16m, com timelapse desligado |

Se uma cópia falhar no meio, o A1 permite pular só aquela peça (cancelar objeto). O Bambu Studio marca cada cópia separadamente no G-code quando a mesa tem de 2 a 64 peças (`GCode.cpp`, `get_labeled_id` por instância). Uma peça que caia continua na mesa, então vale acompanhar as primeiras camadas.

**Ponto de atenção da aceleração 6000.** As paredes internas, o preenchimento e o suporte passam a acelerar a mesa (eixo Y) com mais força, e as peças são altas com pouco contato com a placa. Os perfis padrão do A1 usam 6000, mas se alguma peça soltar no teste, volte esse valor para 4000. Fica em Processo → Velocidade → Aceleração → "Normal printing". Isso custa só ~3,7 min por peça.

## Resultado do fatiamento (validação)

### 1 peça: G-code fatiado no Bambu Studio 02.08.02.60

O arquivo está em `fatiados/` e a análise em `analise/`.

- **Configurações aplicadas.** O cabeçalho traz `wall_generator = arachne`, `cooling_slowdown_logic = consistent_surface`, `default_acceleration = 4000` e `different_settings_to_system = enable_support;seam_position;wall_generator;cooling_slowdown_logic;`, como previsto.
- **Comandos de máquina.** São iguais aos do original: mesmo G-code final e mesmos comandos de controle no corpo. A única diferença no início é a área de nivelamento (`G29`), deslocada 10 mm em X porque a peça está na posição do 3MF.
- **Brilho: parede externa a 60 mm/s em 360 de 398 camadas.** No original eram 152; as faixas de 16–28 mm e 44–64 mm, antes a 23–47 mm/s, agora ficam a 60. As 36 camadas mais lentas são as de base e de topo, com seção mínima.
- **Tempo: 1h29m10s, contra 1h27m11s (+2 min).** O `consistent_surface` desacelera mais o preenchimento e as paredes internas para manter a parede externa rápida. É o custo da uniformidade de brilho quando se imprime uma peça só.
- **Pontas das presas.** O Arachne não as recupera (tabela em `DIAGNOSTICO_E_PLANO.md`, seção 4.5): ele perde 32 de 131 ilhas pequenas; o Clássico perdia 33. A comparação física com a peça de referência decide.

### 4 peças (estimativa do Bambu Studio, pela captura de tela)

| | Tempo da mesa | Por peça |
|---|---:|---:|
| Com timelapse (6m33s de preparo + 12m18s de timelapse + 3h43m) | 4h02m | 1h00m30s |
| **Sem timelapse** (6m33s + 3h43m) | **3h49m30s** | **57m23s** |
| Original, 1 peça sem timelapse (6m33s + ~1h07m45s) | — | ~1h14m |
| Original, 1 peça com timelapse (nome do arquivo) | — | 1h27m11s |

- **Ganho por peça:** −23 % contra o original sem timelapse (−17 min por peça) e −34 % contra o 1h27m do nome do arquivo.
- **Material:** 36,88 g por mesa, 9,22 g por peça (original: 9,44 g).
- **Divergência com a minha projeção.** O Bambu Studio prevê bem menos do que a projeção feita a partir do G-code de 1 peça: 4h37m por mesa sem timelapse. Não consigo explicar os ~47 min de diferença sem o G-code das 4 peças.
- **Como mandar o G-code das 4 peças (44 MB).** Comprima em `.zip` antes de enviar; G-code costuma cair para menos de 1/4 do tamanho. Ou exporte o arquivo fatiado da placa (`.gcode.3mf`), que já vem comprimido.
- **O número que vale** é o tempo real cronometrado da mesa de teste.
