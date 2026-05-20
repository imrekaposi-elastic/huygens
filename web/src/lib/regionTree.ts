import type { RegionTreeNode } from "@/api/types";

export type RegionOption = {
  id: string;
  infrastructure_provider_id: string;
  label: string;
  operational: boolean;
};

export function flattenRegionTree(
  nodes: RegionTreeNode[],
  depth = 0,
): RegionOption[] {
  const out: RegionOption[] = [];
  for (const node of nodes) {
    const prefix = depth > 0 ? `${"—".repeat(depth)} ` : "";
    out.push({
      id: node.id,
      infrastructure_provider_id: node.infrastructure_provider_id,
      label: `${prefix}${node.name} (${node.slug})`,
      operational: node.operational,
    });
    out.push(...flattenRegionTree(node.children, depth + 1));
  }
  return out;
}
