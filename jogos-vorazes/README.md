# Jogos Vorazes: anel tordo × cobra

Otimização do tempo de impressão para Bambu Lab A1 com PLA Silk dourado Masterprint, mantendo brilho e detalhes.

- `DIAGNOSTICO_E_PLANO.md`: diagnóstico (Fase 1) e plano priorizado. **Comece por aqui.**
- `original/`: projeto 3MF e G-code originais, só para leitura, com `SHA256SUMS`. Nunca são alterados.
- `ferramentas/`: scripts Python somente leitura.
  - `analisar_gcode.py`: tempo por operação e por camada, blocos condicionais (timelapse) e desaceleração de resfriamento.
  - `analisar_malha_3mf.py`: conteúdo do 3MF, perfis e medidas da malha.
  - `comparar_gcode_malha.py`: confere se o G-code corresponde à malha e aponta detalhes finos que o fatiador descartou.
  - `projetar_cenarios.py`: projeta o tempo por peça com N peças por mesa, timelapse e aceleração, sem gerar G-code.
- `analise/`: saídas dos scripts para os arquivos originais.
