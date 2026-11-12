import 'leaflet/dist/leaflet.css'

import L from 'leaflet'
import { useEffect, useRef } from 'react'

/**
 * Mapa do local (Leaflet + OpenStreetMap). Usa um círculo como marcador,
 * sem imagens externas. No celular o mapa não "prende" a rolagem da página:
 * arrastar com um dedo rola a tela; para ver em detalhe há "Abrir no mapa".
 */
export default function VenueMap({ lat, lng, label }) {
  const container = useRef(null)

  useEffect(() => {
    if (!container.current) return undefined
    const touch = window.matchMedia('(pointer: coarse)').matches
    const map = L.map(container.current, {
      center: [lat, lng],
      zoom: 16,
      scrollWheelZoom: false,
      dragging: !touch,
      tap: false,
      zoomControl: !touch,
      attributionControl: true,
    })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map)
    L.circleMarker([lat, lng], {
      radius: 10,
      color: '#ffffff',
      weight: 3,
      fillColor: '#15803d',
      fillOpacity: 1,
    })
      .addTo(map)
      .bindTooltip(label, { direction: 'top', offset: [0, -10] })
    return () => map.remove()
  }, [lat, lng, label])

  return (
    <div
      ref={container}
      role="img"
      aria-label={`Mapa: ${label}`}
      // isolate: as camadas do Leaflet (z-index 400+) não passam por cima
      // do cabeçalho e da navegação inferior
      className="relative isolate h-44 w-full overflow-hidden rounded-xl"
    />
  )
}
