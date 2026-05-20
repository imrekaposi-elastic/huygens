import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type ProjectWorkspaceContextValue = {
  agentId: string;
  setAgentId: (id: string) => void;
};

const ProjectWorkspaceContext = createContext<ProjectWorkspaceContextValue | null>(null);

export function ProjectWorkspaceProvider({
  projectId,
  children,
}: {
  projectId: string;
  children: ReactNode;
}) {
  const storageKey = `huy-project-agent:${projectId}`;
  const [agentId, setAgentIdState] = useState(() => sessionStorage.getItem(storageKey) ?? "");

  function setAgentId(id: string) {
    setAgentIdState(id);
    if (id) sessionStorage.setItem(storageKey, id);
    else sessionStorage.removeItem(storageKey);
  }

  useEffect(() => {
    const stored = sessionStorage.getItem(storageKey);
    if (stored) setAgentIdState(stored);
  }, [storageKey]);

  return (
    <ProjectWorkspaceContext.Provider value={{ agentId, setAgentId }}>
      {children}
    </ProjectWorkspaceContext.Provider>
  );
}

export function useProjectWorkspace() {
  const ctx = useContext(ProjectWorkspaceContext);
  if (!ctx) throw new Error("useProjectWorkspace must be used within ProjectWorkspaceProvider");
  return ctx;
}
