/// Etiquetas de estado em português.
///
/// Os estados chegam do backend em inglês (`boarding`, `departed`, `confirmed`)
/// porque são valores de base de dados. O agente e o motorista não têm de ler
/// inglês: a tradução vive aqui, num só lugar, em vez de espalhada por cada
/// ecrã — antes o mesmo estado aparecia traduzido nas viagens e em bruto no
/// fluxo de venda.
library;

/// Estado de uma viagem.
String tripStatusLabel(String status) => switch (status) {
      'scheduled' => 'AGENDADA',
      'boarding' => 'EMBARQUE',
      'departed' => 'EM VIAGEM',
      'paused' => 'PAUSADA',
      'completed' => 'CONCLUÍDA',
      'cancelled' => 'CANCELADA',
      '' => '',
      _ => status.toUpperCase(),
    };

/// Estado de um pagamento ou venda.
String paymentStatusLabel(String status) => switch (status) {
      'pending' => 'PENDENTE',
      'processing' => 'A PROCESSAR',
      'confirmed' => 'CONFIRMADO',
      'paid' => 'PAGO',
      'issued' => 'EMITIDO',
      'failed' => 'FALHADO',
      'cancelled' => 'CANCELADO',
      'expired' => 'EXPIRADO',
      'refunded' => 'REEMBOLSADO',
      '' => '',
      _ => status.toUpperCase(),
    };

/// Estado de um bilhete.
String ticketStatusLabel(String status) => switch (status) {
      'active' => 'ACTIVO',
      'used' => 'USADO',
      'expired' => 'EXPIRADO',
      'cancelled' => 'CANCELADO',
      'refunded' => 'REEMBOLSADO',
      '' => '',
      _ => status.toUpperCase(),
    };
