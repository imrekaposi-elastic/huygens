package server

type Endpoint struct {
	AgentID     string `json:"agent_id"`
	NetworkName string `json:"network_name"`
	VnetCIDR    string `json:"vnet_cidr"`
	TunnelIP    string `json:"tunnel_ip"`
	PrivateKey  string `json:"private_key"`
	PublicKey   string `json:"public_key"`
}

type PlanRequest struct {
	LinkID          string   `json:"link_id"`
	Left            Endpoint `json:"left"`
	Right           Endpoint `json:"right"`
	ListenPortBase  int      `json:"listen_port_base,omitempty"`
}

type WireGuardPeer struct {
	Name       string   `json:"name"`
	PublicKey  string   `json:"public_key"`
	Endpoint   string   `json:"endpoint,omitempty"`
	AllowedIPs []string `json:"allowed_ips"`
}

type SideConfig struct {
	Enabled    bool            `json:"enabled"`
	Interface  string          `json:"interface"`
	ListenPort int             `json:"listen_port"`
	PrivateKey string          `json:"private_key"`
	Address    string          `json:"address"`
	Peers      []WireGuardPeer `json:"peers"`
	VnetRoutes []string        `json:"vnet_routes"`
}

type PlanResponse struct {
	Left  SideConfig `json:"left"`
	Right SideConfig `json:"right"`
}

type RevokeRequest struct {
	LinkID       string `json:"link_id,omitempty"`
	LeftNetwork  string `json:"left_network"`
	RightNetwork string `json:"right_network"`
}
