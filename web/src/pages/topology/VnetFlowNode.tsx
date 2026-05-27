import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";

export type VnetNodeData = {
  networkName: string;
  projectName: string;
  cidr: string | null;
  linkSource?: boolean;
};

export function VnetFlowNode({ data, selected }: NodeProps<Node<VnetNodeData>>) {
  const highlight = selected || data.linkSource;
  return (
    <div
      className={`min-w-[148px] rounded-lg border-2 bg-white px-3 py-2 text-xs shadow-sm dark:bg-slate-800 ${
        highlight
          ? "border-emerald-500 ring-2 ring-emerald-400/40"
          : "border-slate-300 dark:border-slate-600"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-3 !w-3 !border-2 !border-white !bg-emerald-500 dark:!border-slate-800"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !border-2 !border-white !bg-emerald-500 dark:!border-slate-800"
      />
      <div className="font-semibold text-slate-900 dark:text-white">{data.networkName}</div>
      <div className="text-slate-500 dark:text-slate-400">{data.projectName}</div>
      <div className="font-mono text-slate-400 dark:text-slate-500">{data.cidr ?? "no CIDR"}</div>
    </div>
  );
}
