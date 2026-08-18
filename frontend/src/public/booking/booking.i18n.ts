import type { Locale } from "../../lib/i18n";

/**
 * Textos da compra pública, em português e inglês.
 *
 * Vivem aqui e não em `lib/i18n.ts` porque aquele dicionário é do portal de
 * gestão — quem o abre procura rótulos de tabelas e menus, e misturar as duas
 * superfícies faria com que uma mudança de texto do balcão aparecesse na página
 * pública sem ninguém reparar.
 *
 * A chave é a frase portuguesa em minúsculas e sem acentos? Não: é uma chave
 * curta e descritiva. Usar a frase como chave parece prático até ao dia em que
 * se corrige uma gralha e se perde a tradução.
 */
const PT = {
  pageTitle: "Comprar bilhete",
  kicker: "Bilhetes interurbanos",
  title: "Compre a sua viagem",
  sub: "Escolha a data, o lugar e receba o bilhete no telemóvel.",
  backToSite: "Voltar ao site",
  steps: "Etapas da compra",

  stepTrip: "Viagem",
  stepDeparture: "Partida",
  stepOutbound: "Ida",
  stepSeats: "Lugares",
  stepReturn: "Volta",
  stepPax: "Passageiros",
  stepPay: "Pagamento",

  whereTo: "Para onde vai?",
  searchLead: "Indique o percurso, a data da viagem e quantos bilhetes precisa.",
  ticketType: "Tipo de bilhete",
  oneWay: "Só ida",
  roundTrip: "Ida e volta",
  origin: "Origem",
  destination: "Destino",
  searchStops: "Escreva para procurar",
  outboundDate: "Data de ida",
  returnDate: "Data de volta",
  passengersCount: "Passageiros",
  passenger: "passageiro",
  passengersPlural: "passageiros",
  searchTrips: "Procurar partidas",

  tripsTitle: "Partidas disponíveis",
  ticket: "bilhete",
  ticketsPlural: "bilhetes",
  noTrips: "Não há partidas nesta data para o percurso escolhido. Experimente outro dia.",
  vehicle: "Viatura",
  seatsAvailable: "Lugares disponíveis",
  soldOut: "Esgotado",
  onlyNSeats: "Só {n} lugares",
  nSeatsLeft: "{n} lugares livres",
  perPerson: "por pessoa",
  changeSearch: "Alterar pesquisa",

  returnTripsTitle: "Partidas de regresso",
  returnLead: "o mesmo percurso ao contrário",
  noReturn: "Não há regresso nesta data. Escolha outro dia, ou compre só a ida.",
  buyOneWayInstead: "Comprar só a ida",
  back: "Voltar",

  pickSeat: "Escolha o seu lugar",
  pickSeats: "Escolha os {n} lugares",
  returnSeats: "Lugares do regresso",
  noSeatMap: "Esta partida não tem lugares marcados.",
  otherTrip: "Outra partida",
  otherReturn: "Outro regresso",
  continue: "Continuar",
  stillToPick: "Falta escolher {n}",
  departsAt: "partida às",

  whoTravels: "Quem viaja?",
  fullName: "Nome completo",
  nameExample: "Ex.: Maria Sitoe",
  document: "Documento",
  documentNumber: "Número",
  asOnDocument: "Como está no documento",
  nominalTicket: "O bilhete é nominal. Em viagens internacionais o documento é conferido na fronteira.",
  nameOnly: "Basta o nome de quem viaja. Nesta carreira não é preciso documento.",
  emergencyContact: "Contacto de emergência",
  name: "Nome",
  phone: "Telefone",

  payLead: "Confirme os dados e pague com a sua carteira móvel.",
  route: "Percurso",
  outbound: "Ida",
  returnLeg: "Volta",
  departure: "Partida",
  returnDeparture: "Partida da volta",
  totalToPay: "TOTAL A PAGAR",
  equivalentIn: "Equivalente em",
  fxNote: "O débito na carteira móvel é sempre em meticais; o valor em {cur} é indicativo e fica registado no bilhete à taxa de hoje.",
  payPhone: "Telemóvel para pagamento",
  payPhoneHint: "Vai receber um pedido de PIN neste número.",
  emailOptional: "Email (opcional)",
  emailHint: "para receber o bilhete",
  acceptPre: "Li e aceito os",
  termsLink: "Termos e Condições",
  acceptOf: "da",
  pay: "Pagar",
  processing: "A processar…",
  pinNotice: "Confirme o pagamento no seu telemóvel se lhe for pedido o PIN. Não feche esta página.",
  currencyGroup: "Moeda dos preços",

  issued: "Bilhete emitido",
  downloadTicket: "Descarregar bilhete",
  backHome: "Voltar ao início",

  errSearch: "Erro na pesquisa.",
  errPayment: "Erro no pagamento.",
  errSeats: "Não foi possível carregar os lugares.",
  errReturnSeats: "Não foi possível carregar os lugares do regresso.",
  errReturnSearch: "Não foi possível procurar o regresso.",
  errPurchase: "Não foi possível concluir a compra.",
  errServer: "Não foi possível contactar o servidor.",
  errWhoTravels: "Indique quem viaja.",
  errEmergencyName: "Indique o nome do contacto de emergência.",
  errEmergencyPhone: "Indique o telefone do contacto de emergência (9 dígitos).",

  lightTheme: "Tema claro",
  darkTheme: "Tema escuro",
};

const EN: Record<keyof typeof PT, string> = {
  pageTitle: "Buy a ticket",
  kicker: "Intercity tickets",
  title: "Book your journey",
  sub: "Pick the date and seat, and get the ticket on your phone.",
  backToSite: "Back to site",
  steps: "Purchase steps",

  stepTrip: "Journey",
  stepDeparture: "Departure",
  stepOutbound: "Outbound",
  stepSeats: "Seats",
  stepReturn: "Return",
  stepPax: "Passengers",
  stepPay: "Payment",

  whereTo: "Where are you going?",
  searchLead: "Choose the route, the travel date and how many tickets you need.",
  ticketType: "Ticket type",
  oneWay: "One way",
  roundTrip: "Round trip",
  origin: "From",
  destination: "To",
  searchStops: "Type to search",
  outboundDate: "Departure date",
  returnDate: "Return date",
  passengersCount: "Passengers",
  passenger: "passenger",
  passengersPlural: "passengers",
  searchTrips: "Search departures",

  tripsTitle: "Available departures",
  ticket: "ticket",
  ticketsPlural: "tickets",
  noTrips: "No departures on this date for the chosen route. Try another day.",
  vehicle: "Bus",
  seatsAvailable: "Seats available",
  soldOut: "Sold out",
  onlyNSeats: "Only {n} seats",
  nSeatsLeft: "{n} seats left",
  perPerson: "per person",
  changeSearch: "Change search",

  returnTripsTitle: "Return departures",
  returnLead: "the same route, reversed",
  noReturn: "No return on this date. Pick another day, or buy one way only.",
  buyOneWayInstead: "Buy one way only",
  back: "Back",

  pickSeat: "Choose your seat",
  pickSeats: "Choose the {n} seats",
  returnSeats: "Return seats",
  noSeatMap: "This departure has no reserved seating.",
  otherTrip: "Another departure",
  otherReturn: "Another return",
  continue: "Continue",
  stillToPick: "{n} still to choose",
  departsAt: "departs at",

  whoTravels: "Who is travelling?",
  fullName: "Full name",
  nameExample: "e.g. Maria Sitoe",
  document: "Document",
  documentNumber: "Number",
  asOnDocument: "As printed on the document",
  nominalTicket: "The ticket is personal. On international journeys the document is checked at the border.",
  nameOnly: "Just the traveller's name. No document is required on this route.",
  emergencyContact: "Emergency contact",
  name: "Name",
  phone: "Phone",

  payLead: "Confirm the details and pay with your mobile wallet.",
  route: "Route",
  outbound: "Outbound",
  returnLeg: "Return",
  departure: "Departure",
  returnDeparture: "Return departure",
  totalToPay: "TOTAL TO PAY",
  equivalentIn: "Equivalent in",
  fxNote: "The mobile wallet is always charged in meticais; the {cur} amount is indicative and is recorded on the ticket at today's rate.",
  payPhone: "Phone number to pay with",
  payPhoneHint: "You will receive a PIN request on this number.",
  emailOptional: "Email (optional)",
  emailHint: "to receive the ticket",
  acceptPre: "I have read and accept the",
  termsLink: "Terms & Conditions",
  acceptOf: "of",
  pay: "Pay",
  processing: "Processing…",
  pinNotice: "Confirm the payment on your phone if the PIN is requested. Do not close this page.",
  currencyGroup: "Price currency",

  issued: "Ticket issued",
  downloadTicket: "Download ticket",
  backHome: "Back to start",

  errSearch: "Search failed.",
  errPayment: "Payment error.",
  errSeats: "Could not load the seats.",
  errReturnSeats: "Could not load the return seats.",
  errReturnSearch: "Could not search for the return journey.",
  errPurchase: "Could not complete the purchase.",
  errServer: "Could not reach the server.",
  errWhoTravels: "Enter who is travelling.",
  errEmergencyName: "Enter the emergency contact name.",
  errEmergencyPhone: "Enter the emergency contact phone (9 digits).",

  lightTheme: "Light theme",
  darkTheme: "Dark theme",
};

export type BookingKey = keyof typeof PT;

/** Texto na língua escolhida, com `{n}`/`{cur}` substituídos. */
export function bt(locale: Locale, key: BookingKey, vars?: Record<string, string | number>): string {
  const base = (locale === "en" ? EN[key] : PT[key]) ?? PT[key];
  if (!vars) return base;
  return Object.entries(vars).reduce(
    (txt, [k, v]) => txt.replace(new RegExp(`\\{${k}\\}`, "g"), String(v)),
    base,
  );
}
