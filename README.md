# Porta-ampola (pote + tampa rosqueada)

Projeto do Bambu Studio para a impressora Bambu Lab A1 (bico 0,4 mm, PLA genérico).

| Arquivo | O que é |
|---|---|
| `porta-ampola-ajustado-v2.3mf` | **Versão atual para imprimir** |
| `porta-ampola-ajustado.3mf` | v1 (versão impressa anteriormente) |
| `porta-ampola-original.3mf` | Arquivo original, guardado como referência |
| `resumo-ajustes-v2.png` | Corte do pote: original × v2 |
| `resumo-ajustes.png` | Antes/depois do v1 (caminho da parede e furo) |

## v2: furos mais fundos, pote mais baixo, furo um pouco mais folgado

### Furos dos frascos
- **Profundidade de 21,5 mm** (eram 17,5): 21,0 mm de parte reta mais o chanfro de 0,5 mm na boca. Com camadas de 0,16 mm a impressão deve dar uns 21,6 mm, pelo mesmo motivo que o v1 deu ~17,5.
- **Ø17,0 mm reais** (v1: 16,9; original: 16,77 real). São círculos de 360 segmentos, com chanfro de entrada de 0,5 mm × 45°.
- O fundo dos furos não mudou de lugar: a base embaixo deles continua com 2,5 mm, e não havia espessura para descer 4 mm. Os furos cresceram **para cima**, subindo o fundo da cavidade em 4 mm.
- Os centros são os mesmos.

### Pote 2 mm mais baixo
- **Altura de 45 mm** (era 47).
- Os 2 mm saíram da faixa reta do meio do corpo, onde a seção é constante. As 19 caneluras ficaram 2 mm mais curtas e mantiveram o mesmo perfil.
- **Rosca, gargalo, ombro e base não mudaram.** A tampa é a mesma do v1 e rosqueia exatamente como antes (folga radial da rosca 0,10 mm, sem alteração).

### Atenção: altura máxima do frasco
Os frascos ficam na **mesma altura de antes**, porque o fundo do furo não desceu, e o pote ficou 2 mm mais baixo. Por isso o espaço do fundo do furo até o teto da tampa fechada **caiu de 45 para 43 mm**.

**Para a tampa fechar, o frasco (com tampinha) deve ter no máximo uns 42,5 mm.** Se os seus frascos forem mais altos que isso, dá para:
- descer o fundo dos furos 1 mm (a base fica com 1,5 mm), ou
- tirar menos que 2 mm do corpo.

## v1: furos Ø16,9, limpeza da malha, parâmetros mais rápidos (mantidos no v2)

### Malha
- Nenhuma das duas malhas tinha erro estrutural: as duas são fechadas e manifold, sem autointerseção.
- Removido o ruído de tesselação da parede externa: vértices que saíam até 0,011 mm do raio de projeto foram recolocados nos raios exatos (29,5 / 28,5 / 27,5 mm etc.).
- Isso importa porque, com o "arc fitting" ligado (padrão do A1), o Bambu Studio quase não simplifica o contorno (0,0024 mm). Assim o ruído ia direto para o caminho da parede externa.

### Parâmetros de impressão (processo)
| Parâmetro | Original | v1/v2 | Motivo |
|---|---|---|---|
| Gerador de paredes (`wall_generator`) | Clássico | **Arachne** | Corrige a causa principal dos defeitos na parede externa (veja abaixo). |
| Combinar preenchimento (`infill_combination`) | Não | **Sim** | O preenchimento interno é feito a cada 2 camadas. As paredes continuam em 0,16 mm, então não aparece por fora. |

O resto ficou como no original: camada de 0,16 mm, velocidade e aceleração da parede externa, costura, resfriamento e preenchimento gyroid a 9%.

**Causa dos defeitos na parede externa.** Na faixa das caneluras do pote, e na das covinhas da tampa, a parede tem só 1,0 mm (2,0 mm nas nervuras). Com o gerador Clássico, o fatiador:
- colocava "gap fill" em zigue-zague logo atrás da parede externa;
- criava ilhas soltas em cada nervura (~59 deslocamentos/retrações por camada).

O Arachne preenche com linhas de largura variável (~21 deslocamentos por camada). No v2 essa faixa de parede fina ficou com metade da altura, porque o fundo da cavidade subiu.

**Tempo estimado** no PrusaSlicer, com as duas peças e configuração equivalente: original 2h23 → v1 1h57 (−19%). O v2 fica praticamente igual ao v1, e o pote gasta +0,7 g de filamento porque o fundo da cavidade ficou mais grosso.

**Opcional (não aplicado):** camada de 0,20 mm reduz mais ~17% do tempo, mas deixa as linhas de camada um pouco mais visíveis.

## Se precisar de ajuste fino
- **Frasco ainda justo ou folgado:** use "X-Y hole compensation" **só no objeto do pote** (configuração por objeto). +0,025 a +0,05 deixa o furo mais folgado, valores negativos apertam. Não aplique na tampa, porque ali também mudaria a rosca interna.
- **Miniatura:** a imagem de prévia do arquivo ainda mostra o pote antigo. O Bambu Studio atualiza ao fatiar ou salvar.
