import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { PublicOnlyRoute } from '../features/auth/components/PublicOnlyRoute'
import { RequireAuth } from '../features/auth/components/RequireAuth'
import ForgotPasswordPage from '../features/auth/pages/ForgotPasswordPage'
import LoginPage from '../features/auth/pages/LoginPage'
import RegisterPage from '../features/auth/pages/RegisterPage'
import ResetPasswordPage from '../features/auth/pages/ResetPasswordPage'
import AppLayout from '../layouts/AppLayout'
import AuthLayout from '../layouts/AuthLayout'
import HomePage from '../pages/HomePage'
import NotFoundPage from '../pages/NotFoundPage'

export const routes: RouteObject[] = [
  {
    element: <AuthLayout />,
    children: [
      {
        element: <PublicOnlyRoute />,
        children: [
          { path: 'login', element: <LoginPage /> },
          { path: 'register', element: <RegisterPage /> },
        ],
      },
      { path: 'forgot-password', element: <ForgotPasswordPage /> },
      { path: 'reset-password', element: <ResetPasswordPage /> },
    ],
  },
  {
    // Everything outside the public auth pages is private, including paths
    // that only resolve to Not Found, so no route answers before login.
    element: <RequireAuth />,
    children: [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: <HomePage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
