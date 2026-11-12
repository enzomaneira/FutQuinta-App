// Rótulos e formatação para exibição (o banco guarda valores em inglês)

export const POSITION_LABEL = { goalkeeper: 'Goleiro', field: 'Linha' }
export const TYPE_LABEL = { monthly: 'Mensalista', drop_in: 'Avulso' }

// +5511987654321 -> (11) 98765-4321; outros países ficam como estão
export function formatPhone(e164) {
  if (!e164) return ''
  const m = e164.match(/^\+55(\d{2})(\d{4,5})(\d{4})$/)
  return m ? `(${m[1]}) ${m[2]}-${m[3]}` : e164
}

export function whatsappUrl(e164) {
  return `https://wa.me/${e164.replace(/\D/g, '')}`
}
