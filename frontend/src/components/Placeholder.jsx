// Cartão provisório das telas que serão construídas nas próximas etapas
export default function Placeholder({ title, stage, children }) {
  return (
    <section className="rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        {children ?? 'Em construção.'} (etapa {stage})
      </p>
    </section>
  )
}
