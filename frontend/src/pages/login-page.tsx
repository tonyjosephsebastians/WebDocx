import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { ArrowRight, Layers3, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { api } from '../lib/api'
import { useSession } from '../lib/session'

export function LoginPage() {
  const navigate = useNavigate()
  const session = useSession()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [workspaceName, setWorkspaceName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  useEffect(() => {
    if (session.ready && session.token) {
      void navigate({ to: '/' })
    }
  }, [navigate, session.ready, session.token])

  const authMutation = useMutation({
    mutationFn: async () => {
      if (mode === 'register') {
        return api.register({ name, email, password, workspace_name: workspaceName || undefined })
      }
      return api.login({ email, password })
    },
    onSuccess: (response) => {
      session.applyAuthResponse(response)
      toast.success(mode === 'register' ? 'Workspace created.' : 'Signed in.')
      void navigate({ to: '/' })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Unable to authenticate.')
    },
  })

  return (
    <main className="grid min-h-screen gap-8 bg-[radial-gradient(circle_at_top_left,#f6d6a8,transparent_28%),radial-gradient(circle_at_bottom_right,#a4d2cb,transparent_24%),linear-gradient(180deg,#f8f4ed_0%,#efe5d9_100%)] px-6 py-8 lg:grid-cols-[1.1fr_0.9fr] lg:px-10">
      <section className="rounded-[40px] border border-white/60 bg-[linear-gradient(145deg,rgba(37,30,23,0.9),rgba(75,54,30,0.88))] p-8 text-white shadow-[0_40px_120px_rgba(45,28,12,0.28)] lg:p-12">
        <div className="inline-flex items-center gap-3 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs uppercase tracking-[0.24em] text-white/75">
          <Layers3 className="h-4 w-4" />
          DOCX workspace
        </div>
        <h1 className="mt-8 max-w-3xl font-display text-5xl leading-[1.02] text-white lg:text-7xl">
          Build a web-native writing room around your ONLYOFFICE server.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-white/75">
          Upload DOCX files, co-edit in real time, compare revisions into fresh drafts, keep redlines visible, and manage version history without leaving the browser.
        </p>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {[
            'Track edits and legal-style comparison drafts',
            'Invite teammates with reviewer, commenter, or editor roles',
            'Keep a paper-centric workspace around the embedded editor',
          ].map((item) => (
            <div className="rounded-[28px] border border-white/10 bg-white/5 p-5" key={item}>
              <Sparkles className="h-4 w-4 text-amber-300" />
              <p className="mt-4 text-sm leading-6 text-white/78">{item}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="flex items-center justify-center">
        <div className="w-full max-w-xl rounded-[36px] border border-white/70 bg-white/75 p-8 shadow-[0_35px_80px_rgba(58,39,15,0.18)] backdrop-blur lg:p-10">
          <div className="flex rounded-full border border-stone-200 bg-stone-50 p-1">
            {(['login', 'register'] as const).map((item) => (
              <button
                className={item === mode ? 'segment-active' : 'segment'}
                key={item}
                onClick={() => setMode(item)}
                type="button"
              >
                {item === 'login' ? 'Sign in' : 'Create workspace'}
              </button>
            ))}
          </div>

          <form
            className="mt-8 space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              authMutation.mutate()
            }}
          >
            {mode === 'register' ? (
              <>
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-stone-700">Your name</span>
                  <input className="input" onChange={(event) => setName(event.target.value)} required value={name} />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-stone-700">Workspace name</span>
                  <input
                    className="input"
                    onChange={(event) => setWorkspaceName(event.target.value)}
                    placeholder="Tony's editorial room"
                    value={workspaceName}
                  />
                </label>
              </>
            ) : null}

            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-stone-700">Email</span>
              <input
                className="input"
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-stone-700">Password</span>
              <input
                className="input"
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>

            <button className="button-primary mt-4 w-full" disabled={authMutation.isPending} type="submit">
              {authMutation.isPending ? 'Working...' : mode === 'register' ? 'Create workspace' : 'Sign in'}
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
