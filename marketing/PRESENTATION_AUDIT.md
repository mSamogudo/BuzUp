# BusUp Premium Deck - Auditoria de Design

## Entrega criada

- `BusUp-Apresentacao-Premium.pdf`: deck final em PDF, 16:9, 10 slides.
- `BusUp-Apresentacao-Premium.pptx`: versão PowerPoint/Keynote com slides em imagem full-bleed.
- `premium_export/slides/`: PNGs individuais em alta resolução.
- `premium_export/BusUp-Apresentacao-Premium-contact-sheet.jpg`: revisão visual dos slides.
- `build_premium_deck.py`: gerador determinístico da apresentação.

## Problemas encontrados na apresentação anterior

- Formato parecia brochure A4 vertical, não apresentação executiva.
- Hierarquia visual fraca: muitos blocos pequenos, pouco contraste de prioridade.
- Imagens e mockups pareciam gerados ou decorativos, com pouca presença de produto real.
- Falta de assinatura institucional recorrente com `Powered by UpDigital`.
- Screenshots com excesso de ruído visual reduziam a percepção premium.
- Narrativa pouco enterprise: faltavam slides de arquitetura, operação, controlo municipal e rollout.
- CTA final tinha contactos placeholder, o que enfraquece a peça para apresentação comercial.

## Melhorias aplicadas

- Deck reconstruído em 16:9 com linguagem enterprise premium.
- Estrutura narrativa reorganizada: problema, solução, app, POS, portal, controlo municipal, implementação e contacto.
- Mockups premium reaproveitados como proof points visuais.
- Paleta BusUp reforçada: azul-marinho, azul royal e branco.
- Rodapé consistente com `BusUp`, secção do slide e `Powered by UpDigital`.
- Logo UpDigital aplicado como assinatura, com margem e escala ajustadas.
- CTA final limpo, sem telefone/email fictícios.
- Exportações validadas visualmente com folha de contacto.
- Transparência dos cards corrigida: painéis com alpha agora são compostos corretamente antes da exportação.
- Renders AI mais fracos removidos dos slides principais.
- Portal apresentado em janela SaaS minimalista, sem laptop artificial.
- App e POS enquadrados em mockups controlados usando screenshots reais de `marketing/shots`.

## Pendências recomendadas antes da versão comercial final

- Substituir qualquer captura antiga com `BuzUp` ou visual laranja por build atual azul.
- Confirmar contacto comercial real antes de inserir telefone ou email.
- Recolher screenshots finais já sem browser chrome, Android Studio, emulador ou dados de teste.
- Se a apresentação precisar de texto 100% editável, recriar o deck em PowerPoint nativo depois de aprovar a direção visual.
- Validar todos os KPIs com equipa de produto/financeiro antes de enviar a parceiros ou municípios.

## Critério visual para próximas imagens

- Realismo fotográfico, sem aparência de boneco ou render plástico.
- Dispositivos alinhados à perspectiva do ecrã, sem distorção da interface.
- Muito espaço negativo, sombras suaves e iluminação de produto.
- Screens tratados como textura fixa: nada dentro do ecrã deve ser reescrito pelo gerador.
- Sem chrome de browser, toolbars, cursores, ambiente de teste ou marcas de terceiros.
- Quando uma imagem AI não estiver perfeita, preferir composição determinística com screenshot real em device limpo.
