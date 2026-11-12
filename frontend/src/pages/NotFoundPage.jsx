import { Link } from 'react-router'

export default function NotFoundPage() {
  return (
    <div className="py-12 text-center">
      <p className="text-base font-semibold">Página não encontrada</p>
      <Link to="/" className="mt-4 inline-flex min-h-11 items-center text-brand-700 underline">
        Voltar ao início
      </Link>
    </div>
  )
}
