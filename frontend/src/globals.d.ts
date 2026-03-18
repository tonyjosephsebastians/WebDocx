declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (
        elementId: string,
        config: Record<string, unknown>,
      ) => {
        destroyEditor?: () => void
        refreshHistory?: (payload: Record<string, unknown>) => void
        setHistoryData?: (payload: Record<string, unknown>) => void
        setRequestedDocument?: (payload: Record<string, unknown>) => void
        setRevisedFile?: (payload: Record<string, unknown>) => void
      }
    }
  }
}

export {}
