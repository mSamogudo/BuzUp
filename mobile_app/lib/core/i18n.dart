import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'providers.dart';

/// Lightweight in-app i18n: a `Map<String, Map<String, String>>` of
/// translations, scoped per locale, with PT as fallback. No code generation.
///
/// Usage from any widget:
///   final tr = ref.watch(trProvider);
///   Text(tr('home.title'));
///
/// Locale flips via `localeControllerProvider` (toggle in Profile).
class _Translations {
  const _Translations(this._dict);
  final Map<String, String> _dict;

  String call(String key) => _dict[key] ?? key;
}

const Map<String, String> _pt = {
  // common
  'app.name': 'BuzUp Passageiro',
  'common.cancel': 'Cancelar',
  'common.save': 'GUARDAR',
  'common.confirm': 'Confirmar',
  'common.close': 'Fechar',
  'common.retry': 'Tentar de novo',
  'common.copy': 'Copiar',
  'common.copied': 'Copiado.',
  'common.loading': 'A carregar...',
  'common.error': 'Erro',
  'common.refresh': 'Actualizar',
  'common.optional': '(opcional)',
  'common.continue': 'CONTINUAR',
  'common.back': 'Voltar',

  // currency
  'currency.mzn': 'MZN',

  // nav (bottom bar)
  'nav.home': 'Inicio',
  'nav.tickets': 'Bilhetes',
  'nav.packages': 'Pacotes',
  'nav.transactions': 'Movimentos',
  'nav.profile': 'Perfil',

  // splash
  'splash.starting': 'A iniciar...',

  // login
  'login.title': 'BuzUp Passageiro',
  'login.subtitlePhone': 'Inicie sessao com o seu telefone',
  'login.subtitleOtp': 'Introduza o codigo enviado a',
  'login.phoneLabel': 'Telefone',
  'login.phoneHint': '84XXXXXXX',
  'login.send': 'ENVIAR CODIGO',
  'login.enter': 'ENTRAR',
  'login.resendIn': 'Reenviar em',
  'login.resend': 'Reenviar codigo',
  'login.phoneError': 'Telefone deve ter 9 digitos comecando por 8 ou 9 (ex: 84XXXXXXX).',
  'login.otpError': 'Codigo deve ter 6 digitos.',
  'login.subtitleRegister': 'Crie a sua conta para comecar a viajar',
  'login.nameLabel': 'Nome completo',
  'login.nameHint': 'Ex: Maria Joao',
  'login.emailLabel': 'Email',
  'login.nameError': 'Introduza o seu nome completo.',
  'login.createAccount': 'CRIAR CONTA',
  'login.changePhone': 'Alterar telefone',
  'login.poweredBy': 'powered by',

  // home
  'home.hello': 'Ola',
  'home.balanceLabel': 'SALDO DA CARTEIRA',
  'home.showAgent': 'MOSTRE AO AGENTE',
  'home.cardPrefix': 'Cartao',
  'home.buyTicket': 'COMPRAR BILHETE',
  'home.topup': 'Recarregar',
  'home.packages': 'Pacotes',
  'home.transactions': 'Movimentos',
  'home.activePackages': 'PACOTES ACTIVOS',
  'home.noPackages': 'Sem pacote activo. Compre um para descontar nas viagens.',
  'home.loadingWallet': 'A carregar a carteira...',

  // tickets
  'tickets.title': 'Os meus bilhetes',
  'tickets.tabActive': 'ACTIVOS',
  'tickets.tabHistory': 'HISTORICO',
  'tickets.empty.active': 'Sem bilhetes activos.',
  'tickets.empty.history': 'Sem bilhetes no historico.',
  'tickets.loading': 'A carregar bilhetes...',
  'tickets.buy': 'COMPRAR BILHETE',
  'tickets.detail.title': 'Bilhete',
  'tickets.detail.loading': 'A carregar bilhete...',
  'tickets.detail.copyToken': 'Token copiado.',
  'tickets.status.active': 'ACTIVO',
  'tickets.status.used': 'USADO',
  'tickets.status.expired': 'EXPIRADO',
  'tickets.status.cancelled': 'CANCELADO',

  // buy ticket
  'buy.title': 'Comprar bilhete',
  'buy.loadingRoutes': 'A carregar rotas...',
  'buy.route': 'Rota',
  'buy.origin': 'Origem',
  'buy.destination': 'Destino',
  'buy.trip': 'Viagem (opcional)',
  'buy.usePackage': 'Usar pacote especial se disponivel',
  'buy.usePackageHelp': 'Quando activo, desconta primeiro do saldo do pacote.',
  'buy.calculating': 'A calcular...',
  'buy.select': 'Seleccione rota, origem e destino para ver o preco.',
  'buy.summary': 'RESUMO DA COMPRA',
  'buy.baseFare': 'Tarifa base',
  'buy.package': 'Pacote',
  'buy.toPayFromWallet': 'A PAGAR DA CARTEIRA',
  'buy.fullyCovered': 'Totalmente coberto pelo pacote — nada sai da carteira.',
  'buy.payButton': 'PAGAR',
  'buy.useFreePackage': 'USAR PACOTE - GRATIS',

  // topup
  'topup.title': 'Recarregar carteira',
  'topup.amount': 'Valor a recarregar',
  'topup.payerPhone': 'Telefone que paga',
  'topup.pay': 'PAGAR',
  'topup.checking': 'Verificar agora',

  // transactions
  'tx.title': 'Movimentos',
  'tx.empty': 'Sem movimentos ainda.',
  'tx.loading': 'A carregar movimentos...',
  'tx.detail.title': 'Detalhe do movimento',
  'tx.type.topup': 'Recarga',
  'tx.type.fare_debit': 'Viagem',
  'tx.type.refund': 'Reembolso',
  'tx.type.reversal': 'Reversao',
  'tx.type.adjustment': 'Ajuste',
  'tx.type.card_transfer': 'Transferencia',
  'tx.type.fee': 'Taxa',
  'tx.balance': 'Saldo',
  'tx.credit': 'CREDITO',
  'tx.debit': 'DEBITO',

  // extract
  'extract.title': 'Extracto',
  'extract.loading': 'A calcular...',
  'extract.empty': 'Sem movimentos no periodo seleccionado.',
  'extract.credits': 'Creditos',
  'extract.debits': 'Debitos',
  'extract.net': 'Saldo',
  'extract.changeRange': 'Alterar',

  // packages
  'pkg.title': 'Pacotes',
  'pkg.detail.title': 'Detalhes do pacote',
  'pkg.empty.active': 'Sem pacotes activos.',
  'pkg.activeSubs': 'PACOTES ACTIVOS',
  'pkg.available': 'PACOTES DISPONIVEIS',
  'pkg.subscribe': 'COMPRAR PACOTE',
  'pkg.specialBalance': 'SALDO ESPECIAL DISPONIVEL',
  'pkg.freeTrips': 'VIAGENS DISPONIVEIS',
  'pkg.discountActive': 'DESCONTO ACTIVO',

  // profile
  'profile.title': 'Perfil',
  'profile.account': 'Conta',
  'profile.documents': 'Documentos',
  'profile.preferences': 'Preferencias',
  'profile.session': 'Sessao',
  'profile.editProfile': 'Editar perfil',
  'profile.fullName': 'Nome completo',
  'profile.email': 'Email',
  'profile.theme': 'Tema',
  'profile.language': 'Idioma',
  'profile.themeLight': 'Claro',
  'profile.themeDark': 'Escuro',
  'profile.themeSystem': 'Sistema',
  'profile.langPt': 'Portugues',
  'profile.langEn': 'English',
  'profile.extract': 'Extracto da conta',
  'profile.fees': 'Taxas e tarifas',
  'profile.extractPdf': 'Descarregar extracto (PDF)',
  'profile.logout': 'Terminar sessao',
  'profile.balance': 'Saldo',
  'profile.card': 'Cartao',
  'profile.noCard': 'Sem cartao',
  'profile.updated': 'Perfil actualizado.',

  // admin fees
  'fees.title': 'Taxas e tarifas',
  'fees.loading': 'A carregar taxas...',
  'fees.empty': 'Sem taxas activas no momento.',
};

const Map<String, String> _en = {
  // common
  'app.name': 'BuzUp Passenger',
  'common.cancel': 'Cancel',
  'common.save': 'SAVE',
  'common.confirm': 'Confirm',
  'common.close': 'Close',
  'common.retry': 'Try again',
  'common.copy': 'Copy',
  'common.copied': 'Copied.',
  'common.loading': 'Loading...',
  'common.error': 'Error',
  'common.refresh': 'Refresh',
  'common.optional': '(optional)',
  'common.continue': 'CONTINUE',
  'common.back': 'Back',

  'currency.mzn': 'MZN',

  'nav.home': 'Home',
  'nav.tickets': 'Tickets',
  'nav.packages': 'Plans',
  'nav.transactions': 'Activity',
  'nav.profile': 'Profile',

  'splash.starting': 'Starting...',

  'login.title': 'BuzUp Passenger',
  'login.subtitlePhone': 'Sign in with your phone',
  'login.subtitleOtp': 'Enter the code sent to',
  'login.phoneLabel': 'Phone',
  'login.phoneHint': '84XXXXXXX',
  'login.send': 'SEND CODE',
  'login.enter': 'SIGN IN',
  'login.resendIn': 'Resend in',
  'login.resend': 'Resend code',
  'login.phoneError': 'Phone must be 9 digits starting with 8 or 9 (eg. 84XXXXXXX).',
  'login.otpError': 'Code must be 6 digits.',
  'login.subtitleRegister': 'Create your account to start travelling',
  'login.nameLabel': 'Full name',
  'login.nameHint': 'Eg. Maria Joao',
  'login.emailLabel': 'Email',
  'login.nameError': 'Enter your full name.',
  'login.createAccount': 'CREATE ACCOUNT',
  'login.changePhone': 'Change phone',
  'login.poweredBy': 'powered by',

  'home.hello': 'Hi',
  'home.balanceLabel': 'WALLET BALANCE',
  'home.showAgent': 'SHOW TO AGENT',
  'home.cardPrefix': 'Card',
  'home.buyTicket': 'BUY TICKET',
  'home.topup': 'Top up',
  'home.packages': 'Plans',
  'home.transactions': 'Activity',
  'home.activePackages': 'ACTIVE PLANS',
  'home.noPackages': 'No active plan. Buy one to get discounts on trips.',
  'home.loadingWallet': 'Loading wallet...',

  'tickets.title': 'My tickets',
  'tickets.tabActive': 'ACTIVE',
  'tickets.tabHistory': 'HISTORY',
  'tickets.empty.active': 'No active tickets.',
  'tickets.empty.history': 'No tickets in history.',
  'tickets.loading': 'Loading tickets...',
  'tickets.buy': 'BUY TICKET',
  'tickets.detail.title': 'Ticket',
  'tickets.detail.loading': 'Loading ticket...',
  'tickets.detail.copyToken': 'Token copied.',
  'tickets.status.active': 'ACTIVE',
  'tickets.status.used': 'USED',
  'tickets.status.expired': 'EXPIRED',
  'tickets.status.cancelled': 'CANCELLED',

  'buy.title': 'Buy ticket',
  'buy.loadingRoutes': 'Loading routes...',
  'buy.route': 'Route',
  'buy.origin': 'Origin',
  'buy.destination': 'Destination',
  'buy.trip': 'Trip (optional)',
  'buy.usePackage': 'Use special plan if available',
  'buy.usePackageHelp': 'When on, deducts from the plan balance first.',
  'buy.calculating': 'Calculating...',
  'buy.select': 'Select route, origin and destination to see the price.',
  'buy.summary': 'PURCHASE SUMMARY',
  'buy.baseFare': 'Base fare',
  'buy.package': 'Plan',
  'buy.toPayFromWallet': 'TO PAY FROM WALLET',
  'buy.fullyCovered': 'Fully covered by the plan — nothing leaves the wallet.',
  'buy.payButton': 'PAY',
  'buy.useFreePackage': 'USE PLAN - FREE',

  'topup.title': 'Top up wallet',
  'topup.amount': 'Amount to top up',
  'topup.payerPhone': 'Phone that pays',
  'topup.pay': 'PAY',
  'topup.checking': 'Check now',

  'tx.title': 'Activity',
  'tx.empty': 'No activity yet.',
  'tx.loading': 'Loading activity...',
  'tx.detail.title': 'Transaction details',
  'tx.type.topup': 'Top-up',
  'tx.type.fare_debit': 'Trip',
  'tx.type.refund': 'Refund',
  'tx.type.reversal': 'Reversal',
  'tx.type.adjustment': 'Adjustment',
  'tx.type.card_transfer': 'Transfer',
  'tx.type.fee': 'Fee',
  'tx.balance': 'Balance',
  'tx.credit': 'CREDIT',
  'tx.debit': 'DEBIT',

  'extract.title': 'Statement',
  'extract.loading': 'Calculating...',
  'extract.empty': 'No activity in the selected period.',
  'extract.credits': 'Credits',
  'extract.debits': 'Debits',
  'extract.net': 'Balance',
  'extract.changeRange': 'Change',

  'pkg.title': 'Plans',
  'pkg.detail.title': 'Plan details',
  'pkg.empty.active': 'No active plans.',
  'pkg.activeSubs': 'ACTIVE PLANS',
  'pkg.available': 'AVAILABLE PLANS',
  'pkg.subscribe': 'BUY PLAN',
  'pkg.specialBalance': 'AVAILABLE SPECIAL BALANCE',
  'pkg.freeTrips': 'AVAILABLE TRIPS',
  'pkg.discountActive': 'ACTIVE DISCOUNT',

  'profile.title': 'Profile',
  'profile.account': 'Account',
  'profile.documents': 'Documents',
  'profile.preferences': 'Preferences',
  'profile.session': 'Session',
  'profile.editProfile': 'Edit profile',
  'profile.fullName': 'Full name',
  'profile.email': 'Email',
  'profile.theme': 'Theme',
  'profile.language': 'Language',
  'profile.themeLight': 'Light',
  'profile.themeDark': 'Dark',
  'profile.themeSystem': 'System',
  'profile.langPt': 'Portugues',
  'profile.langEn': 'English',
  'profile.extract': 'Account statement',
  'profile.fees': 'Fees and charges',
  'profile.extractPdf': 'Download statement (PDF)',
  'profile.logout': 'Sign out',
  'profile.balance': 'Balance',
  'profile.card': 'Card',
  'profile.noCard': 'No card',
  'profile.updated': 'Profile updated.',

  'fees.title': 'Fees and charges',
  'fees.loading': 'Loading fees...',
  'fees.empty': 'No active fees at the moment.',
};

/// Resolves the current locale to its translations dictionary, with PT as
/// fallback when the active locale isn't bundled (defensive).
final trProvider = Provider<_Translations>((ref) {
  final locale = ref.watch(localeControllerProvider);
  if (locale.languageCode == 'en') return const _Translations(_en);
  return const _Translations(_pt);
});
