/* eslint-disable react-refresh/only-export-components */

import { createRootRoute, createRoute, createRouter, Outlet } from '@tanstack/react-router'
import { Toaster } from 'sonner'

import { EditorPage } from './pages/editor-page'
import { LoginPage } from './pages/login-page'
import { WorkspacePage } from './pages/workspace-page'

function RootLayout() {
  return (
    <>
      <Outlet />
      <Toaster richColors position="top-right" />
    </>
  )
}

const rootRoute = createRootRoute({
  component: RootLayout,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: WorkspacePage,
})

const documentRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/documents/$documentId',
  component: EditorPage,
})

const routeTree = rootRoute.addChildren([loginRoute, indexRoute, documentRoute])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
