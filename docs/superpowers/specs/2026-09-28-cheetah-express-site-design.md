# Site institucional da Cheetah Express

Data: 2026-09-28 · Estado: aprovado, por implementar

## Porquê

A Cheetah Express é operadora de *shuttle* entre Nelspruit (África do Sul) e
Moçambique (Maputo e Tofo) e passa a ser cliente do BuzUp, como já é a TPM-TUR.
O site actual (`cheetah-express.com`, WordPress) entrega as reservas a um
terceiro — `booking.drivenot.com`. O objectivo deste trabalho é substituir esse
site por um servido pelo próprio BuzUp, com a compra feita dentro do sistema.

Sucesso: um visitante chega ao domínio da Cheetah, percebe o serviço, consulta
horários e preços, e compra o bilhete sem sair para outro fornecedor.

## Âmbito

As páginas que o site actual tem, e só essas:

| Rota | Página |
|---|---|
| `/cheetah-express` | Início |
| `/cheetah-express/horarios` | Horários e preços |
| `/cheetah-express/contactos` | Contactos |
| `/cheetah-express/termos` | Condições de transporte |

Em português e inglês. **Fora de âmbito:** páginas institucionais que o site
actual não tem (Sobre nós, Frota, Serviços, Políticas), alterações ao backend,
e qualquer mudança ao tema global da aplicação.

## Decisões tomadas

### 1. Tokens de marca locais à caixa, não preset global

A aplicação inteira carrega hoje o preset da TPM-TUR
(`frontend/src/tailwind.css` → `themes/tpm-tur.css`), e a página `/tpm-tur` lê
essas variáveis. A Cheetah é preto/vermelho/amarelo e não pode herdá-las.

`cheetah.css` redefine as variáveis de marca **dentro de `.bzlp-cheetah`**,
como `.bzlp-tpm` já faz. Nada global muda: o portal de gestão, o login e o site
da TPM-TUR ficam intocados.

Foi considerado e rejeitado, por agora, tirar o preset de global e escolhê-lo
por operador em tempo de execução. É o desenho correcto para um SaaS
multi-cliente, mas mexe no tema de todo o portal e do login — é um projecto por
si, e não a forma de entregar o site de um cliente.

### 2. Partilhar o que é genérico, escrever o que é de marca

Reutilizado sem alteração: o vocabulário `bzlp-*` de `landing.css`,
`useLandingPrefs`, `Reveal`, `StopCombo`, `CampoData`, `CampoSelect`.

**Elevado** de `public/tpm/` para `public/comum/` — duas peças que só estão
presas à TPM-TUR por importarem o texto dela:

| Hoje | Passa a ser | Alteração |
|---|---|---|
| `tpm/HeroBooking.tsx` | `comum/HeroBusca.tsx` | recebe `textos` por propriedade em vez de chamar `useTpmCopy()` |
| `tpm/TpmFormularioPedido.tsx` | `comum/FormularioPedido.tsx` | recebe `textos`, `email`, `telefone`, `telefoneHref`, `prefixoAssunto` |
| ~200 linhas `.tpm-busca-*` de `tpm.css` | `comum/busca.css`, classes `.bz-busca-*` | o CSS já está escrito contra variáveis da caixa, não contra cores fixas |

O CSS partilhado lê variáveis genéricas (`--busca-accao`, `--busca-accao-ink`,
`--busca-superficie`, `--busca-linha`, `--busca-ink`, `--busca-accao-escura`)
que **cada caixa mapeia**: `.bzlp-tpm` para o ciano/navy que já tem,
`.bzlp-cheetah` para vermelho/preto. Os nomes de token próprios da TPM-TUR
(`--navy`, `--blue`, `--gold`) não são tocados.

**Escrito de novo**, porque é onde as marcas legitimamente divergem: casca
(barra, menu, rodapé), texto PT/EN, CSS de marca e as quatro páginas. A casca
da TPM-TUR serve seis páginas com FAQ; a da Cheetah serve quatro com tabelas de
horários. Forçá-las a um molde comum seria abstrair a partir de dois casos, um
deles ainda por escrever.

**Risco conhecido:** o lift é a única parte que toca em trabalho já entregue.
Uma regressão visual em `/tpm-tur` é o modo de falha, e é verificável (ver
Verificação).

### 3. Idioma segue o navegador

`useLandingPrefs` já escolhe pelo idioma do navegador — inglês se o navegador
for inglês, senão português. Serve os dois públicos da rota (sul-africano e
moçambicano) sem código novo.

A versão `/pt/` do site oficial é tradução automática em português do Brasil
("ônibus", "você", "Transportador" para *shuttles*). **Não se copia.** O
português deste site é de Moçambique, como o da TPM-TUR.

### 4. Condições de transporte escritas de novo

A página "Terms and Conditions" do site actual **não são os termos da Cheetah**:
são os termos SaaS do `drivenot.com`. Nomeiam esse fornecedor, dão-lhe
exclusividade de sistema de reservas em Moçambique e são regidos por lei
sul-africana. Publicá-los no site novo seria pôr, em nome da Cheetah, o
contrato do fornecedor que o BuzUp vem substituir.

Escrevem-se condições de transporte a partir do que a operação real diz —
horários de embarque, bagagem, documentos para a travessia de fronteira,
cancelamentos, preços — marcadas **POR APROVAR** pela Cheetah, com a mesma
convenção que `tpm-copy.ts` usa para o texto institucional que é da empresa e
não nosso.

## Marca

Preto `#141618`, vermelho `#EA1D23`, amarelo `#F8C70F`. Tipo DM Sans (o site
oficial usa-a).

Contrastes medidos, não supostos:

| Par | Rácio | Serve para |
|---|---|---|
| branco sobre vermelho | 4,47:1 | botões e títulos; **não** corpo de texto |
| preto sobre amarelo | 11,37:1 | qualquer texto |
| branco sobre amarelo | 1,59:1 | **proibido** |
| amarelo sobre preto | 11,37:1 | rodapé escuro |
| branco sobre preto | 18,14:1 | rodapé escuro |
| vermelho sobre branco | 4,47:1 | títulos e acções |

Regra que fica escrita no CSS: **texto sobre amarelo é sempre preto; o vermelho
pinta acções e títulos, nunca parágrafos.**

## Conteúdo

Origem: `cheetah-express.com` (autorizado pelo cliente da UpDigital).
Logótipo e fotografias descarregados de lá; o texto é reescrito, não copiado,
excepto os factos (horas, paragens, preços).

### Início
- Hero fotográfico com o cartão de pesquisa (`comum/HeroBusca`).
  "Seguro, fiável e rápido" · "O seu transporte n.º 1 entre Nelspruit e Moçambique".
- Quatro provas: totalmente climatizado · mais de 10 anos de experiência ·
  motoristas experientes · Wi-Fi a bordo.
- Três serviços: shuttle diário Maputo–Nelspruit (inclui o Drop & Shop, lançado
  com a Go Nelspruit e o Ilanga Mall); shuttles Tofo–Maputo–Nelspruit;
  excursões à medida a partir de aeroportos.
- Parceiros: Ilanga Mall, Riverside Mall, Go Nelspruit, Mediplus, Medi-evac, Casa.
- Chamada final: ver horários / pedir orçamento de grupo.

### Horários
Cinco quadros, com paragens, horas e preço:

1. **Maputo–Nelspruit**, diário. Mundo's 05:30 · Matola Shoprite 06:00 →
   Ilanga 09:30 · Riverside 10:00. Regresso: Riverside 15:30 · Ilanga 16:00 →
   Matola 20:00 · Mundo's 20:30. R450 / ±1800 MT, só ida.
2. **Tofo–Maputo–Nelspruit**, terças e sextas, com dormida.
3. **Nelspruit–Maputo–Tofo**, domingos e quartas, com dormida.
4. **Tofo–Maputo**, terças e sextas. R600 / ±2500 MT.
5. **Maputo–Tofo**, segundas e quintas. 2500 MT.

Tabela em ecrã largo, cartões abaixo de 768px: uma tabela de três colunas a
390px é ilegível.

### Contactos
Formulário (`comum/FormularioPedido`), que **prepara um email e não submete
nada** — pelo mesmo motivo documentado em `TpmFormularioPedido`: o único
endereço público de formulários, `POST /api/public/service-requests/`, é o
funil de vendas do BusUp, não tem campo de operador e notifica o telefone
comercial da UpDigital.

Contactos: `bookings@cheetah-express.com` (reservas),
`cheetahexpressmaputo@gmail.com` (geral), Maputo, Moçambique, 1100.

## Ficheiros

Novos:
```
frontend/src/public/comum/HeroBusca.tsx
frontend/src/public/comum/FormularioPedido.tsx
frontend/src/public/comum/busca.css
frontend/src/public/cheetah/CheetahChrome.tsx
frontend/src/public/cheetah/cheetah-copy.ts
frontend/src/public/cheetah/cheetah.css
frontend/src/public/cheetah/CheetahLandingPage.tsx
frontend/src/public/cheetah/HorariosPage.tsx
frontend/src/public/cheetah/ContactosPage.tsx
frontend/src/public/cheetah/TermosPage.tsx
frontend/public/assets/cheetah-logo/
frontend/public/landing/cheetah/
```

Alterados:
```
frontend/src/App.tsx                      quatro rotas lazy
frontend/src/public/tpm/tpm.css           sai o bloco .tpm-busca-*, entra o mapa de tokens
frontend/src/public/tpm/tpm-paginas.css   idem para o bloco do formulário
frontend/src/public/tpm/TpmTurLandingPage.tsx   passa os textos ao HeroBusca
frontend/src/public/tpm/ContactosPage.tsx       passa os textos ao FormularioPedido
```

Removidos (movidos): `tpm/HeroBooking.tsx`, `tpm/TpmFormularioPedido.tsx`.

## Instância e dados

Cada cliente corre a sua instância (`mobile_app/config/tpmtur.env` →
`tpm-tur.updigital.co.mz`); a Cheetah terá a sua, com base de dados própria.
Por isso `/api/public/trips/?sellable=1` devolve, na instância da Cheetah, as
paragens da Cheetah, e o hero de pesquisa funciona **sem alterações ao
backend**.

Consequência registada, não resolvida: sendo o repositório um só, a rota
`/cheetah-express` também existe na instância da TPM-TUR, onde mostraria dados
da TPM-TUR. Ninguém lá chega — não há link e o domínio é outro — mas é o que é:
uma consequência de um repositório com várias instâncias.

O backend é hoje explicitamente mono-inquilino: `BrandingSettings` é uma linha
única e não existe modelo de operador. Este trabalho não altera isso.

## Verificação

- `tsc` sem erros.
- **`/tpm-tur` comparado antes e depois do lift** — claro e escuro, 1440px e
  390px. É o único sítio onde este trabalho pode partir coisa já entregue.
- As quatro páginas novas vistas no container Docker, nos dois idiomas e nos
  dois temas.
- Contrastes medidos no browser, não deduzidos.
- Tabelas de horários verificadas a 390px.

Dois factos desta base a acautelar: o Vite serve módulos em cache mesmo com o
disco sincronizado — confirma-se a correcção no browser e, se preciso,
reinicia-se o `buzup_frontend_dev`; e o Tailwind está sem *preflight*, portanto
os defaults do browser estão vivos e as tabelas precisam de reset explícito.
