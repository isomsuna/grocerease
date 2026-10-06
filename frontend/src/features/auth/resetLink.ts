import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

export type ResetLink = { uid: string; token: string }

const STORAGE_KEY = 'grocerease.password-reset-link'

function readStoredResetLink(): ResetLink | null {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? 'null')
    const { uid, token } = (value ?? {}) as Partial<Record<keyof ResetLink, unknown>>
    return typeof uid === 'string' && typeof token === 'string' ? { uid, token } : null
  } catch {
    return null
  }
}

function storeResetLink(link: ResetLink): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(link))
  } catch {
    // Without storage the link still works until the page is reloaded.
  }
}

export function clearStoredResetLink(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing stored.
  }
}

/**
 * Reads the uid/token from the emailed reset link, keeps them for this tab
 * only, and removes them from the address bar so a still-valid link does not
 * stay visible or reachable through back navigation. A reload of the clean
 * URL picks the link up from tab storage, as Django's reset view does with
 * its session.
 */
export function useResetLink(): ResetLink | null {
  const location = useLocation()
  const navigate = useNavigate()
  const params = new URLSearchParams(location.search)
  const linkInUrl = params.has('uid') || params.has('token')

  const [link] = useState<ResetLink | null>(() => {
    if (!linkInUrl) {
      return readStoredResetLink()
    }
    const uid = params.get('uid')
    const token = params.get('token')
    return uid && token ? { uid, token } : null
  })

  useEffect(() => {
    if (!linkInUrl) {
      return
    }
    if (link) {
      storeResetLink(link)
    } else {
      clearStoredResetLink()
    }
    void navigate({ pathname: location.pathname, hash: location.hash }, { replace: true })
  }, [linkInUrl, link, navigate, location.pathname, location.hash])

  return link
}
