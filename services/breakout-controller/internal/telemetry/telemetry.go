// Package telemetry configures OpenTelemetry traces and metrics (ADR 0008).
package telemetry

import (
	"context"
	"net/url"
	"os"
	"strings"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.41.0"
)

const defaultServiceName = "huy-breakout-controller"

// Init installs global TracerProvider and MeterProvider. OTLP export is enabled when
// OTEL_EXPORTER_OTLP_ENDPOINT is set. Returns a shutdown function.
func Init(ctx context.Context) (func(context.Context) error, error) {
	if sdkDisabled() {
		return func(context.Context) error { return nil }, nil
	}

	serviceName := os.Getenv("OTEL_SERVICE_NAME")
	if serviceName == "" {
		serviceName = defaultServiceName
	}

	extra := parseResourceAttributes()
	attrs := make([]attribute.KeyValue, 0, len(extra)+1)
	attrs = append(attrs, semconv.ServiceName(serviceName))
	attrs = append(attrs, extra...)

	res, err := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(semconv.SchemaURL, attrs...),
	)
	if err != nil {
		return nil, err
	}

	var shutdownFuncs []func(context.Context) error

	tracerProvider := sdktrace.NewTracerProvider(sdktrace.WithResource(res))
	if endpoint := otlpEndpoint(); endpoint != "" {
		traceExporter, err := newTraceExporter(ctx, endpoint)
		if err != nil {
			return nil, err
		}
		tracerProvider = sdktrace.NewTracerProvider(
			sdktrace.WithResource(res),
			sdktrace.WithBatcher(traceExporter),
		)
		shutdownFuncs = append(shutdownFuncs, traceExporter.Shutdown)
	}
	otel.SetTracerProvider(tracerProvider)
	shutdownFuncs = append(shutdownFuncs, tracerProvider.Shutdown)

	meterProvider := sdkmetric.NewMeterProvider(sdkmetric.WithResource(res))
	if endpoint := otlpEndpoint(); endpoint != "" {
		metricExporter, err := newMetricExporter(ctx, endpoint)
		if err != nil {
			return nil, err
		}
		reader := sdkmetric.NewPeriodicReader(metricExporter, sdkmetric.WithInterval(30*time.Second))
		meterProvider = sdkmetric.NewMeterProvider(
			sdkmetric.WithResource(res),
			sdkmetric.WithReader(reader),
		)
		shutdownFuncs = append(shutdownFuncs, metricExporter.Shutdown)
	}
	otel.SetMeterProvider(meterProvider)
	shutdownFuncs = append(shutdownFuncs, meterProvider.Shutdown)

	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	shutdown := func(ctx context.Context) error {
		var firstErr error
		for i := len(shutdownFuncs) - 1; i >= 0; i-- {
			if err := shutdownFuncs[i](ctx); err != nil && firstErr == nil {
				firstErr = err
			}
		}
		return firstErr
	}
	return shutdown, nil
}

func sdkDisabled() bool {
	return strings.EqualFold(strings.TrimSpace(os.Getenv("OTEL_SDK_DISABLED")), "true")
}

func otlpEndpoint() string {
	return strings.TrimSpace(os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
}

func otlpProtocol() string {
	p := strings.TrimSpace(os.Getenv("OTEL_EXPORTER_OTLP_PROTOCOL"))
	if p == "" {
		return "grpc"
	}
	return strings.ToLower(p)
}

func parseResourceAttributes() []attribute.KeyValue {
	raw := strings.TrimSpace(os.Getenv("OTEL_RESOURCE_ATTRIBUTES"))
	if raw == "" {
		return nil
	}
	var attrs []attribute.KeyValue
	for _, part := range strings.Split(raw, ",") {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		k, v, ok := strings.Cut(part, "=")
		if !ok {
			continue
		}
		attrs = append(attrs, attribute.String(strings.TrimSpace(k), strings.TrimSpace(v)))
	}
	return attrs
}

func useHTTPExporter() bool {
	p := otlpProtocol()
	return p == "http" || p == "http/protobuf"
}

func grpcEndpoint(hostURL string) (string, error) {
	u, err := url.Parse(hostURL)
	if err != nil {
		return strings.TrimPrefix(strings.TrimPrefix(hostURL, "http://"), "https://"), nil
	}
	if u.Host != "" {
		return u.Host, nil
	}
	return hostURL, nil
}

func newTraceExporter(ctx context.Context, endpoint string) (sdktrace.SpanExporter, error) {
	if useHTTPExporter() {
		return otlptracehttp.New(ctx, otlptracehttp.WithEndpointURL(endpoint))
	}
	host, err := grpcEndpoint(endpoint)
	if err != nil {
		return nil, err
	}
	return otlptracegrpc.New(ctx, otlptracegrpc.WithEndpoint(host), otlptracegrpc.WithInsecure())
}

func newMetricExporter(ctx context.Context, endpoint string) (sdkmetric.Exporter, error) {
	if useHTTPExporter() {
		return otlpmetrichttp.New(ctx, otlpmetrichttp.WithEndpointURL(endpoint))
	}
	host, err := grpcEndpoint(endpoint)
	if err != nil {
		return nil, err
	}
	return otlpmetricgrpc.New(ctx, otlpmetricgrpc.WithEndpoint(host), otlpmetricgrpc.WithInsecure())
}
