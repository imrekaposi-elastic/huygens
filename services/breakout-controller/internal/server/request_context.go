package server

import (
	"net/http"

	"github.com/google/uuid"
	"go.opentelemetry.io/otel/trace"
)

// requestContextMiddleware sets X-Request-Id and X-Trace-Id (aligned with huy_telemetry Python services).
func requestContextMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := r.Header.Get("X-Request-Id")
		if requestID == "" {
			requestID = uuid.NewString()
		}
		w.Header().Set("X-Request-Id", requestID)

		span := trace.SpanFromContext(r.Context())
		if span.SpanContext().IsValid() {
			w.Header().Set("X-Trace-Id", span.SpanContext().TraceID().String())
		}

		next.ServeHTTP(w, r)
	})
}
