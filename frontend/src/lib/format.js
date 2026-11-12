// Rótulos e formatação para exibição (o banco guarda valores em inglês)

export const POSITION_LABEL = { goalkeeper: 'Goleiro', field: 'Linha' }
export const TYPE_LABEL = { monthly: 'Mensalista', drop_in: 'Avulso' }

// +5511987654321 -> (11) 98765-4321; outros países ficam como estão
export function formatPhone(e164) {
  if (!e164) return ''
  const m = e164.match(/^\+55(\d{2})(\d{4,5})(\d{4})$/)
  return m ? `(${m[1]}) ${m[2]}-${m[3]}` : e164
}

export const GAME_STATUS = {
  draft: { label: 'Rascunho', tone: 'neutral' },
  open: { label: 'Lista aberta', tone: 'green' },
  closed: { label: 'Lista fechada', tone: 'blue' },
  played: { label: 'Realizado', tone: 'neutral' },
  cancelled: { label: 'Cancelado', tone: 'red' },
}

export const ATTENDANCE_STATUS = {
  pending: { label: 'Pendente', tone: 'amber' },
  confirmed: { label: 'Confirmado', tone: 'green' },
  cancelled: { label: 'Desmarcou', tone: 'neutral' },
  released: { label: 'Perdeu a vaga', tone: 'neutral' },
  queued: { label: 'Na fila', tone: 'blue' },
  present: { label: 'Compareceu', tone: 'green' },
  absent: { label: 'Faltou', tone: 'red' },
}

const WEEKDAYS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado']

// "2026-11-19" -> Date local (sem conversão de fuso)
export function parseLocalDate(isoDate) {
  const [y, m, d] = isoDate.split('-').map(Number)
  return new Date(y, m - 1, d)
}

// "2026-11-19" -> "quinta, 19/11"
export function formatGameDate(isoDate) {
  const date = parseLocalDate(isoDate)
  const dd = String(date.getDate()).padStart(2, '0')
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  return `${WEEKDAYS[date.getDay()]}, ${dd}/${mm}`
}

// "21:30" -> "21h30"
export function formatTime(hhmm) {
  return hhmm.replace(':', 'h')
}

// Data/hora (UTC da API) no fuso do jogo -> "qui 12h00"
export function formatDeadline(isoDateTime) {
  const parts = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).formatToParts(new Date(isoDateTime))
  const get = (type) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('weekday').replace('.', '')} ${get('hour')}h${get('minute')}`
}

export function formatMoney(cents) {
  return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export function whatsappUrl(e164) {
  return `https://wa.me/${e164.replace(/\D/g, '')}`
}
