package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/config"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/server"
)

func main() {
	cfg := config.Load()
	srv := server.New(cfg)
	httpSrv := &http.Server{Addr: cfg.Addr, Handler: srv.Handler()}

	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = httpSrv.Shutdown(ctx)
	}()

	log.Printf("huy-ssh-gateway listening on %s", cfg.Addr)
	if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
	_ = srv.Close()
}
