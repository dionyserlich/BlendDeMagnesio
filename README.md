> Outros projetos neste repositório:
> - [`jogos-vorazes/`](jogos-vorazes/): anel tordo × cobra em PLA Silk dourado. Diagnóstico de tempo e plano de otimização para a Bambu Lab A1.

# Porta-ampola (pote + tampa rosqueada)

Projeto do Bambu Studio para a impressora Bambu Lab A1 com bico de 0,4 mm e PLA genérico.

- `porta-ampola-ajustado.3mf`: versão para imprimir.
- `porta-ampola-original.3mf`: arquivo original, guardado como referência.
- `resumo-ajustes.png`: imagem com o antes e depois.

## O que mudou no `porta-ampola-ajustado.3mf`

### Furos dos frascos (pote)
- Os 4 furos passaram de Ø16,8 mm para **Ø16,9 mm reais**. O original era um polígono de 54 lados: nos vértices media 16,8, mas o diâmetro útil (entre faces) era só 16,77 mm.
- Os furos agora são círculos de 360 segmentos, então o diâmetro útil é de fato 16,9 mm em toda a profundidade (17,5 mm).
- Na boca de cada furo foi feito um **chanfro de entrada de 0,5 mm × 45°** para guiar o frasco ao encaixar.
- Centros, profundidade e fundo dos furos continuam iguais.

### Malha (pote e tampa)
- Nenhuma das duas malhas tinha erro estrutural. As duas são fechadas e manifold, com normais consistentes e sem autointerseção.
- Removido o ruído de tesselação na parede externa. Os vértices dos cilindros saíam até 0,011 mm do raio de projeto e foram recolocados exatamente nos raios de 29,5 / 28,5 / 27,5 mm etc. A forma não muda.
- Por que isso importa: com o "arc fitting" ligado (padrão do A1), o Bambu Studio quase não simplifica o contorno de cada camada (0,0024 mm). Assim esse ruído ia direto para o caminho da parede externa.
- A rosca, as caneluras, as covinhas da tampa e todas as outras medidas ficaram iguais.

### Parâmetros de impressão (processo)
| Parâmetro | Antes | Depois | Motivo |
|---|---|---|---|
| Gerador de paredes (`wall_generator`) | Clássico | **Arachne** | Corrige a causa principal dos defeitos na parede externa (veja abaixo). |
| Combinar preenchimento (`infill_combination`) | Não | **Sim** | O preenchimento esparso interno é feito a cada 2 camadas (0,32 mm). As paredes continuam em 0,16 mm, então não aparece por fora. |

O resto ficou igual: camada de 0,16 mm, velocidades e acelerações da parede externa, costura, resfriamento e preenchimento gyroid a 9%.

**Causa dos defeitos na parede externa.** Na faixa das caneluras do pote, e na faixa das covinhas da tampa, a parede tem só 1,0 mm (2,0 mm nas nervuras). Com o gerador Clássico, o fatiador:
- coloca "gap fill" em zigue-zague logo atrás da parede externa;
- cria ilhas soltas em cada uma das 18 nervuras, com cerca de 59 deslocamentos/retrações por camada.

O Arachne usa linhas de largura variável que preenchem a parede sem gap fill, com cerca de 21 deslocamentos por camada.

**Tempo estimado** no PrusaSlicer, com as duas peças juntas e configuração equivalente: **2h23 → 1h57 (−19%)**. O tempo absoluto no Bambu Studio vai ser diferente, mas a proporção deve ser parecida.

**Opcional (não aplicado):** trocar a camada para 0,20 mm (perfil "0.20mm Standard") levaria a cerca de 1h37 (−32%). Só que as linhas de camada ficam um pouco mais visíveis, principalmente nas pontas arredondadas das caneluras e na rosca.

Se o frasco ainda ficar justo, ajuste o "X-Y hole compensation" (ex.: +0,05 mm) **só no objeto do pote**, como configuração por objeto. Assim não precisa editar o modelo de novo. Não aplique na tampa: lá ele também alargaria a rosca interna.
