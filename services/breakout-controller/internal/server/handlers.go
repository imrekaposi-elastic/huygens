package server

import (
	"encoding/json"
	"fmt"
	"net/http"
)

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "huy-breakout-controller"})
}

func (s *Server) handlePlan(w http.ResponseWriter, r *http.Request) {
	var req PlanRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "invalid JSON"})
		return
	}
	if req.Left.NetworkName == "" || req.Right.NetworkName == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "left and right endpoints required"})
		return
	}
	if req.Left.PrivateKey == "" || req.Right.PrivateKey == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "private keys required on endpoints"})
		return
	}
	basePort := req.ListenPortBase
	if basePort == 0 {
		basePort = 51820
	}
	leftPort := basePort
	rightPort := basePort + 1

	leftIface := fmt.Sprintf("wg-%s", sanitize(req.Left.NetworkName))
	rightIface := fmt.Sprintf("wg-%s", sanitize(req.Right.NetworkName))

	leftAllowed := []string{req.Right.TunnelIP + "/32"}
	if req.Right.VnetCIDR != "" {
		leftAllowed = append(leftAllowed, req.Right.VnetCIDR)
	}
	rightAllowed := []string{req.Left.TunnelIP + "/32"}
	if req.Left.VnetCIDR != "" {
		rightAllowed = append(rightAllowed, req.Left.VnetCIDR)
	}

	leftRoutes := []string{}
	if req.Left.VnetCIDR != "" {
		leftRoutes = append(leftRoutes, req.Left.VnetCIDR)
	}
	rightRoutes := []string{}
	if req.Right.VnetCIDR != "" {
		rightRoutes = append(rightRoutes, req.Right.VnetCIDR)
	}

	resp := PlanResponse{
		Left: SideConfig{
			Enabled:    true,
			Interface:  leftIface,
			ListenPort: leftPort,
			PrivateKey: req.Left.PrivateKey,
			Address:    req.Left.TunnelIP + "/32",
			VnetRoutes: leftRoutes,
			Peers: []WireGuardPeer{
				{
					Name:       "link-" + req.Right.NetworkName,
					PublicKey:  req.Right.PublicKey,
					AllowedIPs: leftAllowed,
				},
			},
		},
		Right: SideConfig{
			Enabled:    true,
			Interface:  rightIface,
			ListenPort: rightPort,
			PrivateKey: req.Right.PrivateKey,
			Address:    req.Right.TunnelIP + "/32",
			VnetRoutes: rightRoutes,
			Peers: []WireGuardPeer{
				{
					Name:       "link-" + req.Left.NetworkName,
					PublicKey:  req.Left.PublicKey,
					AllowedIPs: rightAllowed,
				},
			},
		},
	}
	writeJSON(w, http.StatusOK, resp)
}

func (s *Server) handleRevoke(w http.ResponseWriter, r *http.Request) {
	var req RevokeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "invalid JSON"})
		return
	}
	if req.LeftNetwork == "" || req.RightNetwork == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "left_network and right_network required"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"disabled":       true,
		"link_id":        req.LinkID,
		"left_network":   req.LeftNetwork,
		"right_network":  req.RightNetwork,
	})
}

func sanitize(name string) string {
	out := make([]byte, 0, len(name))
	for i := 0; i < len(name); i++ {
		c := name[i]
		if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') {
			out = append(out, c)
		} else {
			out = append(out, '-')
		}
	}
	if len(out) == 0 {
		return "vnet"
	}
	return string(out)
}
