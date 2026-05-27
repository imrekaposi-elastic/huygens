package main

import (
	"log"
	"net/http"
	"os"

	"github.com/imrekaposi-elastic/huygens/services/breakout-controller/internal/server"
)

func main() {
	addr := os.Getenv("HUY_BREAKOUT_HOST")
	if addr == "" {
		addr = "0.0.0.0:8085"
	}
	token := os.Getenv("BREAKOUT_SERVICE_TOKEN")
	if token == "" {
		token = "dev-breakout-service-token"
	}
	srv := server.New(token)
	log.Printf("huy-breakout-controller listening on %s", addr)
	if err := http.ListenAndServe(addr, srv.Handler()); err != nil {
		log.Fatal(err)
	}
}
