package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/imrekaposi-elastic/huygens/services/breakout-controller/internal/server"
	"github.com/imrekaposi-elastic/huygens/services/breakout-controller/internal/telemetry"
)

func main() {
	ctx := context.Background()
	shutdownTelemetry, err := telemetry.Init(ctx)
	if err != nil {
		log.Fatalf("telemetry: %v", err)
	}
	defer func() {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := shutdownTelemetry(shutdownCtx); err != nil {
			log.Printf("telemetry shutdown: %v", err)
		}
	}()

	addr := os.Getenv("HUY_BREAKOUT_HOST")
	if addr == "" {
		addr = "0.0.0.0:8085"
	}
	token := os.Getenv("BREAKOUT_SERVICE_TOKEN")
	if token == "" {
		token = "dev-breakout-service-token"
	}
	srv := server.New(token)

	httpSrv := &http.Server{
		Addr:    addr,
		Handler: srv.Handler(),
	}

	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = httpSrv.Shutdown(shutdownCtx)
	}()

	log.Printf("huy-breakout-controller listening on %s", addr)
	if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
