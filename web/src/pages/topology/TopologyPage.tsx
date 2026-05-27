import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Connection,
  type Edge,
  type Node,
  type NodeTypes,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { TopologyLinkEdge, TopologyVnetNode } from "@/api/types";
import { Modal } from "@/components/Modal";
import { VnetFlowNode, type VnetNodeData } from "@/pages/topology/VnetFlowNode";

const nodeTypes: NodeTypes = { vnet: VnetFlowNode };

function vnetNodeId(v: TopologyVnetNode): string {
  return `${v.agent_id}:${v.project_id}:${v.network_name}`;
}

function endpointId(e: { agent_id: string; project_id: string; network_name: string }): string {
  return `${e.agent_id}:${e.project_id}:${e.network_name}`;
}

function statusColor(status: string): string {
  switch (status) {
    case "connected":
      return "border-emerald-500 text-emerald-700 dark:text-emerald-300";
    case "error":
      return "border-red-500 text-red-700 dark:text-red-300";
    case "applying":
    case "pending":
      return "border-amber-500 text-amber-700 dark:text-amber-300";
    default:
      return "border-slate-400 text-slate-600 dark:text-slate-400";
  }
}

type Props = { organizationId: string };

function TopologyCanvas({ organizationId }: Props) {
  const queryClient = useQueryClient();
  const [selectedLinkId, setSelectedLinkId] = useState<string | null>(null);
  const [pendingConnection, setPendingConnection] = useState<Connection | null>(null);
  const [linkSourceId, setLinkSourceId] = useState<string | null>(null);
  const [overlayPoolId, setOverlayPoolId] = useState("");
  const [linkError, setLinkError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { data: topology, refetch: refetchTopology } = useQuery({
    queryKey: ["topology", organizationId],
    queryFn: () => api.topology(organizationId),
    refetchInterval: 15000,
  });

  const { data: pools } = useQuery({
    queryKey: ["ipam-pools", organizationId],
    queryFn: () => api.listIpamPools(organizationId),
  });

  const overlayPools = useMemo(
    () => (pools ?? []).filter((p) => p.pool_kind === "overlay"),
    [pools],
  );

  useEffect(() => {
    if (!overlayPoolId && overlayPools.length > 0) {
      setOverlayPoolId(overlayPools[0].id);
    }
  }, [overlayPools, overlayPoolId]);

  const initialNodes: Node<VnetNodeData>[] = useMemo(() => {
    if (!topology) return [];
    return topology.vnets.map((v, i) => ({
      id: vnetNodeId(v),
      type: "vnet",
      position: { x: (i % 4) * 240, y: Math.floor(i / 4) * 140 },
      data: {
        networkName: v.network_name,
        projectName: v.project_name ?? v.project_id.slice(0, 8),
        cidr: v.ipv4_cidr,
        linkSource: false,
      },
    }));
  }, [topology]);

  const initialEdges: Edge[] = useMemo(() => {
    if (!topology) return [];
    return topology.links
      .map((link: TopologyLinkEdge) => {
        const label =
          link.link_type === "local"
            ? `${link.left_tunnel_address} ↔ ${link.right_tunnel_address} (local, ${link.status})`
            : `${link.left_tunnel_address} ↔ ${link.right_tunnel_address} (${link.status})`;
        return {
          id: link.id,
          source: endpointId(link.left),
          target: endpointId(link.right),
          label: link.config_drift ? `${label} · drift` : label,
          animated: link.status === "applying" || link.status === "pending",
          style: {
            stroke: link.config_drift
              ? "#f97316"
              : link.status === "connected"
                ? "#10b981"
                : "#f59e0b",
            strokeDasharray: link.link_type === "local" ? "6 4" : undefined,
          },
        };
      })
      .filter((e) => e.source && e.target);
  }, [topology]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(
      initialNodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          linkSource: n.id === linkSourceId,
        },
      })),
    );
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, linkSourceId, setNodes, setEdges]);

  const openLinkDialog = useCallback((connection: Connection) => {
    if (!connection.source || !connection.target || connection.source === connection.target) {
      return;
    }
    setPendingConnection(connection);
    setLinkSourceId(null);
    setLinkError(null);
  }, []);

  const onConnect = useCallback(
    (connection: Connection) => {
      openLinkDialog(connection);
    },
    [openLinkDialog],
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node<VnetNodeData>) => {
      if (!linkSourceId) {
        setLinkSourceId(node.id);
        setLinkError(null);
        return;
      }
      if (linkSourceId === node.id) {
        setLinkSourceId(null);
        return;
      }
      openLinkDialog({
        source: linkSourceId,
        target: node.id,
        sourceHandle: null,
        targetHandle: null,
      });
    },
    [linkSourceId, openLinkDialog],
  );

  const onPaneClick = useCallback(() => {
    setLinkSourceId(null);
  }, []);

  const { data: linkDetail } = useQuery({
    queryKey: ["network-link", organizationId, selectedLinkId],
    queryFn: () => api.getNetworkLink(organizationId, selectedLinkId!),
    enabled: !!selectedLinkId,
  });

  const pendingLocalLink = useMemo(() => {
    if (!pendingConnection?.source || !pendingConnection.target || !topology) {
      return false;
    }
    const left = topology.vnets.find((v) => vnetNodeId(v) === pendingConnection.source);
    const right = topology.vnets.find((v) => vnetNodeId(v) === pendingConnection.target);
    return !!(left && right && left.agent_id === right.agent_id);
  }, [pendingConnection, topology]);

  const distinctAgentIds = useMemo(
    () => new Set((topology?.vnets ?? []).map((v) => v.agent_id)),
    [topology],
  );

  const pendingNeedsSecondAgent = useMemo(() => {
    if (!pendingConnection?.source || !pendingConnection.target || !topology || pendingLocalLink) {
      return false;
    }
    const left = topology.vnets.find((v) => vnetNodeId(v) === pendingConnection.source);
    const right = topology.vnets.find((v) => vnetNodeId(v) === pendingConnection.target);
    if (!left || !right) return false;
    return left.agent_id !== right.agent_id && distinctAgentIds.size < 2;
  }, [pendingConnection, topology, pendingLocalLink, distinctAgentIds]);

  async function confirmCreateLink() {
    if (!pendingConnection?.source || !pendingConnection.target || !topology) {
      return;
    }
    if (!pendingLocalLink && !overlayPoolId) {
      setLinkError("Create an overlay IPAM pool first (IPAM → Overlay).");
      return;
    }
    const left = topology.vnets.find((v) => vnetNodeId(v) === pendingConnection.source);
    const right = topology.vnets.find((v) => vnetNodeId(v) === pendingConnection.target);
    if (!left || !right) {
      setLinkError("Could not resolve vnet endpoints.");
      return;
    }
    setBusy(true);
    setLinkError(null);
    try {
      await api.createNetworkLink(organizationId, {
        ...(pendingLocalLink ? {} : { overlay_pool_id: overlayPoolId }),
        left: {
          agent_id: left.agent_id,
          project_id: left.project_id,
          network_name: left.network_name,
        },
        right: {
          agent_id: right.agent_id,
          project_id: right.project_id,
          network_name: right.network_name,
        },
      });
      setPendingConnection(null);
      await refetchTopology();
      void queryClient.invalidateQueries({ queryKey: ["topology", organizationId] });
    } catch (e) {
      setLinkError(e instanceof ApiError ? e.message : "Failed to create link");
    } finally {
      setBusy(false);
    }
  }

  async function deleteSelectedLink() {
    if (!selectedLinkId) return;
    setBusy(true);
    try {
      await api.deleteNetworkLink(organizationId, selectedLinkId);
      setSelectedLinkId(null);
      await refetchTopology();
    } catch (e) {
      setLinkError(e instanceof ApiError ? e.message : "Failed to delete link");
    } finally {
      setBusy(false);
    }
  }

  const vnetCount = topology?.vnets.length ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Topology</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Drag from the green dot on one vnet to another, or click a source vnet then a target vnet.
          </p>
        </div>
        <button
          type="button"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600"
          onClick={() => void refetchTopology()}
        >
          Refresh
        </button>
      </div>

      {linkSourceId && (
        <p className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200">
          Source vnet selected — click a second vnet to link, or drag from its right handle to another
          vnet&apos;s left handle.
        </p>
      )}

      {overlayPools.length === 0 && distinctAgentIds.size >= 2 && (
        <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
          No overlay pool yet. In IPAM, create an overlay pool (e.g. 10.255.0.0/24) before cross-hypervisor
          WireGuard links.
        </p>
      )}

      {vnetCount < 2 && (
        <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
          {vnetCount === 0
            ? "No project vnets yet. Assign networks to projects under Projects → Networks, then refresh."
            : "You need at least two vnets on the canvas to create a link."}
        </p>
      )}

      <div className="h-[min(70vh,640px)] rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-950">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          onEdgeClick={(_, edge) => setSelectedLinkId(edge.id)}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>

      {pendingConnection && (
        <Modal
          open
          title={pendingLocalLink ? "Create local link (same hypervisor)" : "Create network link"}
          onClose={() => setPendingConnection(null)}
          footer={
            <>
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm text-slate-600"
                onClick={() => setPendingConnection(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white disabled:opacity-50"
                onClick={() => void confirmCreateLink()}
              >
                Create link
              </button>
            </>
          }
        >
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
            Connect <strong>{formatNodeLabel(pendingConnection.source, topology?.vnets)}</strong> to{" "}
            <strong>{formatNodeLabel(pendingConnection.target, topology?.vnets)}</strong>
            {pendingLocalLink ? (
              <>
                {" "}
                on the <strong>same hypervisor</strong>. Direct routing via iptables (NAT exempt +
                forward between vnet CIDRs) — no WireGuard tunnel.
              </>
            ) : (
              <> via WireGuard breakout.</>
            )}
          </p>
          {pendingNeedsSecondAgent && (
            <p className="mb-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
              Cross-hypervisor links need a <strong>second enrolled agent</strong> in this organization.
              The link may stay in <strong>error</strong> until another hypervisor is connected.
            </p>
          )}
          {!pendingLocalLink && (
            <>
              <label className="block text-sm font-medium">Overlay pool</label>
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                value={overlayPoolId}
                onChange={(e) => setOverlayPoolId(e.target.value)}
              >
                {overlayPools.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.cidr})
                  </option>
                ))}
              </select>
            </>
          )}
          {linkError && <p className="mt-2 text-sm text-red-600">{linkError}</p>}
        </Modal>
      )}

      {selectedLinkId && linkDetail && (
        <aside className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-start justify-between gap-2">
            <h2 className="font-semibold">Link detail</h2>
            <button
              type="button"
              className="text-sm text-slate-500"
              onClick={() => setSelectedLinkId(null)}
            >
              Close
            </button>
          </div>
          <p
            className={`mt-2 inline-block rounded border px-2 py-0.5 text-xs ${statusColor(linkDetail.status)}`}
          >
            {linkDetail.status}
          </p>
          <dl className="mt-3 grid gap-2 text-sm">
            <div>
              <dt className="text-slate-500">Type</dt>
              <dd className="capitalize">{linkDetail.link_type}</dd>
            </div>
            {linkDetail.config_drift && (
              <div>
                <dt className="text-slate-500">Config drift</dt>
                <dd className="text-amber-700 dark:text-amber-300">
                  Agent breakout differs from desired state
                </dd>
              </div>
            )}
            <div>
              <dt className="text-slate-500">
                {linkDetail.link_type === "local" ? "Routed networks" : "Tunnel"}
              </dt>
              <dd>
                {linkDetail.left_tunnel_address} ↔ {linkDetail.right_tunnel_address}
                {linkDetail.link_type !== "local" && ` (${linkDetail.tunnel_cidr})`}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Left</dt>
              <dd>
                {linkDetail.left.network_name} on agent {linkDetail.left.agent_id.slice(0, 8)}…
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Right</dt>
              <dd>
                {linkDetail.right.network_name} on agent {linkDetail.right.agent_id.slice(0, 8)}…
              </dd>
            </div>
            {linkDetail.last_error && (
              <div>
                <dt className="text-slate-500">Last error</dt>
                <dd className="text-red-600">{linkDetail.last_error}</dd>
              </div>
            )}
          </dl>
          <button
            type="button"
            disabled={busy}
            className="mt-4 rounded-lg border border-red-300 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:text-red-300"
            onClick={() => void deleteSelectedLink()}
          >
            Delete link
          </button>
        </aside>
      )}

      {linkError && !pendingConnection && <p className="text-sm text-red-600">{linkError}</p>}
    </div>
  );
}

function formatNodeLabel(nodeId: string | null | undefined, vnets: TopologyVnetNode[] | undefined) {
  if (!nodeId || !vnets) return nodeId ?? "?";
  const v = vnets.find((vn) => vnetNodeId(vn) === nodeId);
  return v ? `${v.project_name ?? "project"}/${v.network_name}` : nodeId;
}

export function TopologyPage(props: Props) {
  return (
    <ReactFlowProvider>
      <TopologyCanvas {...props} />
    </ReactFlowProvider>
  );
}
