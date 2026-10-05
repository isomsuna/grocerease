import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <section aria-labelledby="not-found-title" className="not-found">
      <p className="eyebrow">404</p>
      <h1 id="not-found-title">Page not found</h1>
      <p>The page you’re looking for doesn’t exist or may have moved.</p>
      <Link to="/">Return to GrocerEase</Link>
    </section>
  )
}
