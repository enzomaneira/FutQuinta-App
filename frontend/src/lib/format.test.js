import { describe, expect, it } from 'vitest'

import {
  formatDeadline,
  formatGameDate,
  formatMoney,
  formatPhone,
  formatShortDate,
  formatTime,
  mapsUrl,
  parseMoney,
  whatsappUrl,
} from './format.js'

// toLocaleString usa espaço não separável entre "R$" e o valor
const plain = (text) => text.replace(/ /g, ' ')

describe('parseMoney (campos de valor em reais)', () => {
  it.each([
    ['59', 5900],
    ['59,00', 5900],
    ['25,5', 2550],
    ['1.200,00', 120000],
    ['1200,50', 120050],
    ['R$ 245,00', 24500],
    [' 80 ', 8000],
    ['0,01', 1],
  ])('%s -> %i centavos', (text, cents) => {
    expect(parseMoney(text)).toBe(cents)
  })

  it.each(['', 'abc', '12,3,4'])('%s é inválido', (text) => {
    expect(Number.isNaN(parseMoney(text))).toBe(true)
  })
})

describe('formatMoney', () => {
  it('formata centavos em reais', () => {
    expect(plain(formatMoney(5900))).toBe('R$ 59,00')
    expect(plain(formatMoney(120050))).toBe('R$ 1.200,50')
    expect(plain(formatMoney(-8000))).toBe('-R$ 80,00')
  })
})

describe('telefone', () => {
  it('formata celular e fixo brasileiros', () => {
    expect(formatPhone('+5511987654321')).toBe('(11) 98765-4321')
    expect(formatPhone('+551134567890')).toBe('(11) 3456-7890')
  })

  it('mantém número estrangeiro e trata vazio', () => {
    expect(formatPhone('+14155550100')).toBe('+14155550100')
    expect(formatPhone(null)).toBe('')
  })

  it('gera link do WhatsApp só com dígitos', () => {
    expect(whatsappUrl('+5511987654321')).toBe('https://wa.me/5511987654321')
  })
})

describe('datas e horários', () => {
  it('mostra o dia da semana sem conversão de fuso', () => {
    expect(formatGameDate('2026-11-19')).toBe('quinta, 19/11')
    expect(formatGameDate('2026-03-01')).toBe('domingo, 01/03')
  })

  it('formata hora e data curta', () => {
    expect(formatTime('21:30')).toBe('21h30')
    expect(formatShortDate('2026-12-15')).toBe('15/12')
  })

  it('mostra prazos no horário de São Paulo, qualquer que seja o fuso do celular', () => {
    // 15:00 UTC = 12:00 em São Paulo (quinta)
    expect(formatDeadline('2026-11-19T15:00:00Z')).toBe('qui 12h00')
    expect(formatDeadline('2026-11-19T21:00:00Z')).toBe('qui 18h00')
  })

  it('gera link para abrir no mapa', () => {
    expect(mapsUrl(-23.5899, -46.6355)).toBe(
      'https://www.google.com/maps/search/?api=1&query=-23.5899,-46.6355',
    )
  })
})
