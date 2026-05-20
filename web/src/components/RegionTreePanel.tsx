import type { RegionTreeNode } from "@/api/types";

type Props = {
  nodes: RegionTreeNode[];
  depth?: number;
};

export function RegionTreePanel({ nodes, depth = 0 }: Props) {
  if (!nodes.length) {
    return <p className="text-sm text-slate-500">No regions yet.</p>;
  }
  return (
    <ul className={depth === 0 ? "space-y-2" : "ml-4 mt-2 space-y-2 border-l border-slate-700 pl-3"}>
      {nodes.map((node) => (
        <li key={node.id} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{node.name}</span>
            <span className="font-mono text-xs text-slate-500">{node.slug}</span>
            {node.operational ? (
              <span className="rounded bg-emerald-950 px-2 py-0.5 text-xs text-emerald-300">
                operational
              </span>
            ) : (
              <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                no agent coverage
              </span>
            )}
            {node.has_direct_agent && (
              <span className="text-xs text-slate-400">agent on this node</span>
            )}
            {node.descendant_agent_count > 0 && (
              <span className="text-xs text-slate-500">
                {node.descendant_agent_count} agent(s) in subtree
              </span>
            )}
          </div>
          {node.agents.length > 0 && (
            <ul className="mt-2 space-y-1 text-sm text-slate-400">
              {node.agents.map((a) => (
                <li key={a.id} className="font-mono text-xs">
                  {a.name} · {a.agent_technology_slug} · {a.connection_status}
                </li>
              ))}
            </ul>
          )}
          {node.children.length > 0 && <RegionTreePanel nodes={node.children} depth={depth + 1} />}
        </li>
      ))}
    </ul>
  );
}
