export function formatMediaType(mediaType: string) {
  const mediaTypes: Record<string, string> = {
    game: 'Jogo',
    comic: 'Quadrinho',
  }

  return mediaTypes[mediaType] ?? mediaType
}

export function formatStatus(status: string) {
  const statuses: Record<string, string> = {
    monitoring: 'Em monitoramento',
    released: 'Lançado',
    archived: 'Arquivado',
  }

  return statuses[status] ?? status
}

export function formatAlertType(alertType: string) {
  const alertTypes: Record<string, string> = {
    review_bombing: 'Queda brusca nas avaliações',
    hype_surge: 'Aumento repentino de hype',
    sentiment_drop: 'Queda de sentimento',
    high_controversy: 'Alta controvérsia',
  }

  return alertTypes[alertType] ?? alertType
}

export function formatSeverity(severity: string) {
  const severities: Record<string, string> = {
    low: 'Baixa',
    medium: 'Média',
    high: 'Alta',
  }

  return severities[severity] ?? severity
}

export function formatDate(date: string | null) {
  if (!date) return 'Data não informada'

  return new Date(date).toLocaleDateString('pt-BR')
}

export function translateKeyword(keyword: string) {
  const keywords: Record<string, string> = {
    beautiful: 'bonito',
    angry: 'raiva',
    fans: 'fãs',
    worried: 'preocupação',
    promising: 'promissor',
    divided: 'dividido',
    ambitious: 'ambicioso',
    absolute: 'absolute',
    trailer: 'trailer',
    price: 'preço',
    direction: 'direção',
    atmosphere: 'atmosfera',
    mechanics: 'mecânicas',
  }

  return keywords[keyword.toLowerCase()] ?? keyword
}

export function translateAlertMessage(message: string) {
  const messages: Record<string, string> = {
    'Resident Evil Requiem teve aumento expressivo de sentimento positivo após novo trailer.':
      'Resident Evil Requiem teve um aumento expressivo de sentimento positivo após o novo trailer.',

    'Batman: Year One Absolute tem elogios ao produto, mas críticas recorrentes ao preço.':
      'Batman: Year One Absolute tem elogios ao produto, mas também críticas recorrentes ao preço.',
  }

  return messages[message] ?? message
}