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
  - As cópias ficam em linha ao longo de X, com a mesma orientação do original. Entre uma peça e outra só a cabeça se move; a mesa (eixo Y) não faz movimentos longos com as peças altas em cima, que tocam a placa em só 8 mm².
  - Espaçamento:
    - 45 mm entre os centros;
    - 26,0 mm entre as malhas (o "Organizar" do Bambu reserva 24 mm com suporte em árvore);
    - 18,2 mm entre as áreas de suporte.
  - A área de cada cópia, medida no G-code original e já com os suportes, é de 26,8 × 66,8 mm. O conjunto ocupa X 47–209 e Y 93–160, longe das bordas e da zona de detecção de bico enrolado (X ≥ 226, Y ≥ 224).
- **Aceleração padrão 6000.** Vale para parede interna, preenchimento, sólidos internos, gap fill, ponte e suporte. **Parede externa, saliências e topo continuam em 2000**, e a primeira camada continua em 500. 6000 é o valor dos perfis Standard e Optimal do A1.
- **Arachne.** Imprime as pontas finas (bico e presas, Z 56–63 mm) que o gerador Clássico descartava. Detalhes entre 0,1 e 0,34 mm saem como linha de 0,34 mm; abaixo de 0,1 mm não são impressos.
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
   - `comparar_gcode_malha.py`: se as pontas finas voltaram;
   - `projetar_cenarios.py`.

   Com isso confiro se o ganho previsto se confirma e se nada inesperado mudou.

## Teste de impressão e critérios

Imprima uma mesa com as 4 peças e compare com a peça que você já tem, impressa com o G-code original. Use o mesmo rolo e a mesma placa. Tempo projetado: **~4h16m de impressão real** (~1h04m por peça), contra ~1h15m por peça hoje sem timelapse. É uma projeção sobre os caminhos antigos; o Arachne pode mudar um pouco esse número.

| Critério | Como avaliar | Aprovado se |
|---|---|---|
| Brilho | Uma luz só, a 45°, câmera fixa, peça girada em 4 posições | Sem faixas horizontais, principalmente em 16–28 mm e 44–64 mm. As 4 peças com o mesmo tom. Igual ou melhor que a peça de referência |
| Detalhes | Lupa nas cabeças, escamas e penas | Pontas do bico e das presas presentes. Escamas nítidas, sem bolhas |
| Dimensões | Paquímetro | Altura 64,05 mm, Y 64,2 mm, X 19,0 mm, todos ±0,2 mm, e iguais à peça de referência |
| Defeitos | Inspeção | Sem fios entre as peças, sem marcas novas de suporte, sem queda nas saliências, sem pé de elefante e sem deslocamento de camada |
| Tempo | Cronômetro, do início ao fim da mesa | No máximo ~5 % acima de 4h16m, com timelapse desligado |

Se uma cópia falhar no meio, o A1 permite pular só aquela peça (cancelar objeto). O Bambu Studio marca cada cópia separadamente no G-code quando a mesa tem de 2 a 64 peças (`GCode.cpp`, `get_labeled_id` por instância). Uma peça que caia continua na mesa, então vale acompanhar as primeiras camadas.

**Ponto de atenção da aceleração 6000.** As paredes internas, o preenchimento e o suporte passam a acelerar a mesa (eixo Y) com mais força, e as peças são altas com pouco contato com a placa. Os perfis padrão do A1 usam 6000, mas se alguma peça soltar no teste, volte esse valor para 4000. Fica em Processo → Velocidade → Aceleração → "Normal printing". Isso custa só ~3,7 min por peça.
