// Peças visuais reutilizadas pelas telas (mobile-first, alvos de toque >= 44px)

const BUTTON_VARIANTS = {
  primary: 'bg-brand-700 text-white active:bg-brand-800',
  secondary:
    'bg-neutral-200 text-neutral-900 active:bg-neutral-300 dark:bg-neutral-800 dark:text-neutral-100 dark:active:bg-neutral-700',
  danger: 'bg-red-600 text-white active:bg-red-700',
  ghost: 'text-neutral-700 active:bg-neutral-200 dark:text-neutral-200 dark:active:bg-neutral-800',
}

export function Button({ variant = 'primary', className = '', ...props }) {
  return (
    <button
      type="button"
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-base font-semibold disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
      {...props}
    />
  )
}

export function Card({ as: Tag = 'section', className = '', ...props }) {
  return (
    <Tag
      className={`rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900 ${className}`}
      {...props}
    />
  )
}

const BADGE_TONES = {
  neutral: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  green: 'bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-100',
  amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200',
  red: 'bg-red-100 text-red-800 dark:bg-red-900/60 dark:text-red-200',
  blue: 'bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-200',
}

// Status sempre com texto, a cor só reforça
export function Badge({ tone = 'neutral', children }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${BADGE_TONES[tone]}`}
    >
      {children}
    </span>
  )
}

/** Botões lado a lado para escolher uma opção (ex.: Goleiro / Linha) */
export function Segmented({ options, value, onChange, label }) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="grid gap-1 rounded-xl bg-neutral-200 p-1 dark:bg-neutral-800"
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={`min-h-11 rounded-lg px-2 text-sm font-semibold ${
              selected
                ? 'bg-white text-neutral-900 shadow-sm dark:bg-neutral-950 dark:text-neutral-100'
                : 'text-neutral-600 dark:text-neutral-400'
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

export const inputClass =
  'mt-1 block min-h-12 w-full rounded-xl border border-neutral-300 bg-white px-3 text-base outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-600/30 dark:border-neutral-700 dark:bg-neutral-900'

export function TextField({ label, hint, ...props }) {
  return (
    <label className="block text-sm font-medium">
      {label}
      <input className={inputClass} {...props} />
      {hint && <span className="mt-1 block text-xs text-neutral-600 dark:text-neutral-400">{hint}</span>}
    </label>
  )
}

export function EmptyState({ children }) {
  return (
    <p className="rounded-2xl border border-dashed border-neutral-300 p-6 text-center text-sm text-neutral-600 dark:text-neutral-400 dark:border-neutral-700">
      {children}
    </p>
  )
}

export function LoadingList() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Carregando">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-16 motion-safe:animate-pulse rounded-2xl bg-neutral-200 dark:bg-neutral-800" />
      ))}
    </div>
  )
}

/** Botão flutuante de ação principal, acima da navegação inferior */
export function Fab({ children, ...props }) {
  return (
    <button
      type="button"
      className="fixed right-4 bottom-[calc(5rem+env(safe-area-inset-bottom))] z-30 inline-flex min-h-14 items-center gap-2 rounded-full bg-brand-700 px-5 text-base font-semibold text-white shadow-lg active:bg-brand-800"
      {...props}
    >
      {children}
    </button>
  )
}
