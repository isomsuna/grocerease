export function Logo() {
  return (
    <span className="logo">
      <span className="logo-mark" aria-hidden="true">
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.25"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M5 19c0-9 6-14 15-14 0 9-5 15-14 15M5 19l7-7" />
        </svg>
      </span>
      <span className="logo-word">
        Grocer<span>Ease</span>
      </span>
    </span>
  )
}
