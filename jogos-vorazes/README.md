# Jogos Vorazes: anel tordo × cobra

Otimização do tempo de impressão para Bambu Lab A1 com PLA Silk dourado Masterprint, mantendo brilho e detalhes.

- `DIAGNOSTICO_E_PLANO.md`: diagnóstico (Fase 1) e plano priorizado. **Comece por aqui.**
- `ETAPA_B.md`: os dois projetos prontos para fatiar, como fatiar e enviar, e os critérios do teste de impressão.
- `ETAPA_C.md`: testes de preenchimento combinado (C1) e paredes verticais em "parcial" (C2).
- `variantes/`: projetos gerados a partir do original, com `SHA256SUMS`.
  - `Jogos_Vorazes_producao_4pecas_C3_furos095.3mf`: **produção atual**: C3 com os furos das cabeças em Ø0,95 mm (`edicoes/furos_095.json`).
  - `Jogos_Vorazes_producao_4pecas_C3_combinado.3mf`: C3 (Etapas B + C aprovadas), com os furos originais de Ø0,70.
  - `Jogos_Vorazes_producao_4pecas.3mf`: produção da Etapa B (base das variantes C).
  - `Jogos_Vorazes_1peca.3mf`: para pedidos de uma peça.
  - `Jogos_Vorazes_producao_4pecas_C1_preenchimento.3mf`, `..._C2_paredes_verticais.3mf`: testes da Etapa C.
- `original/`: projeto 3MF e G-code originais, só para leitura, com `SHA256SUMS`. Nunca são alterados.
- `fatiados/`: G-codes fatiados pelo Bambu Studio a partir das variantes, guardados para validação (com `SHA256SUMS`).
- `ferramentas/`: scripts Python somente leitura.
  - `analisar_gcode.py`: tempo por operação e por camada, blocos condicionais (timelapse) e desaceleração de resfriamento.
  - `analisar_malha_3mf.py`: conteúdo do 3MF, perfis e medidas da malha.
  - `comparar_gcode_malha.py`: confere se o G-code corresponde à malha e aponta detalhes finos que o fatiador descartou.
  - `projetar_cenarios.py`: projeta o tempo por peça com N peças por mesa, timelapse e aceleração, sem gerar G-code.
  - `gerar_variante_3mf.py`: gera um projeto novo a partir do original, copiando a malha byte a byte e alterando só as configurações e as instâncias pedidas.
  - `conferir_variante_3mf.py`: compara uma variante com o original (arquivos, configurações, instâncias, posição na mesa).
  - `editar_malha_3mf.py`: aplica edições booleanas na malha (furos, cortes) e prova que nada mudou fora delas (requer `manifold3d`).
- `edicoes/`: edições de malha aplicadas com `editar_malha_3mf.py`.
- `analise/`: saídas dos scripts para os arquivos originais e para os fatiados.
