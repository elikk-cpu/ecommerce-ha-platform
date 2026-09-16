Stage 20 — Performance and Load Testing with k6

Goal

Measure application performance under increasing load, identify saturation behavior, define a tested sustainable checkout rate, and correlate load-test results with platform observability.

Test target

Production VIP:

https://10.20.20.100

Traffic path:

k6
  -> HAProxy VIP
  -> FastAPI app1/app2
  -> PostgreSQL
  -> Redis
  -> RabbitMQ
  -> MinIO

TLS

The internal ecommerce Root CA was installed into the ci-runner system trust store so k6 and curl could validate the production TLS certificate without disabling certificate verification.

Baseline test

Scenario:

- 1 VU
- 30 seconds
- GET /health
- GET /ready

Result:

- checks: 100%
- HTTP failures: 0.00%
- average latency: ~26.49 ms
- p95 latency: ~55.7 ms
- requests: 58
- iterations: 29

Result: PASS

Health/readiness concurrency test

1 VU:
- p95: ~55.7 ms
- errors: 0%

5 VU:
- p95: ~77.48 ms
- errors: 0%
- requests: 570
- iterations: 285

20 VU:
- p95: ~115.92 ms
- errors: 0%
- requests: 2238
- iterations: 1119

50 VU:
- p95: ~372.08 ms
- errors: 0%
- requests: 4950
- iterations: 2475

100 VU:
- average latency: ~487.85 ms
- p90: ~1.51 s
- p95: ~1.68 s
- max: ~2.64 s
- errors: 0%
- requests: 6164
- iterations: 3082
- threshold p95 < 500 ms: FAILED

Finding:

The platform remained available with zero request failures, but readiness-path latency increased sharply between 50 and 100 concurrent VUs.

Checkout smoke test

Scenario:

- 1 iteration
- POST /checkout

Result:

- checkout HTTP success: PASS
- order created: PASS
- order_id returned: PASS
- p95: ~83.07 ms
- HTTP failures: 0%

Result: PASS

Checkout concurrency tests

5 VU:
- average latency: ~91.76 ms
- p90: ~126.4 ms
- p95: ~141.14 ms
- max: ~216.9 ms
- errors: 0%
- iterations: 276
- throughput: ~4.55 checkout/s

20 VU:
- average latency: ~104.6 ms
- p90: ~146.13 ms
- p95: ~183.53 ms
- max: ~487.28 ms
- errors: 0%
- iterations: 1093
- throughput: ~17.98 checkout/s

50 VU:
- average latency: ~312.51 ms
- p90: ~563.08 ms
- p95: ~743.71 ms
- max: ~1.5 s
- errors: 0%
- iterations: 2302
- throughput: ~37.68 checkout/s

100 VU:
- average latency: ~1.26 s
- p90: ~2.07 s
- p95: ~2.25 s
- max: ~2.89 s
- errors: 0%
- iterations: 2697
- throughput: ~43.25 checkout/s
- threshold p95 < 1 s: FAILED

Finding:

Checkout throughput stopped scaling linearly after approximately 40 checkout/s. Increasing concurrency beyond this point primarily increased latency.

Ramping arrival-rate stress test

Scenario:

- 20 RPS
- 40 RPS
- 60 RPS
- 80 RPS
- maxVUs: 200

Result:

- p95 latency: ~4.67 s
- HTTP failures: ~6.93%
- checks passed: ~93.06%
- requests: 4601
- dropped iterations: 498
- max VUs reached: 200/200

k6 reported:

Insufficient VUs, reached 200 active VUs and cannot initialize more

Finding:

The system entered a real saturation state. Request latency increased, failures appeared, and k6 could no longer maintain the requested arrival rate.

Constant arrival-rate capacity tests

SLO used for sustainable capacity:

- p95 latency < 1 second
- HTTP error rate < 1%
- dropped iterations = 0

40 RPS

- actual throughput: ~39.94 checkout/s
- p95: ~679.17 ms
- HTTP failures: 0.00%
- checks: 100%
- dropped iterations: 0
- max active VUs: 55

Result: PASS

42 RPS

- actual throughput: ~41.90 checkout/s
- p95: ~697.32 ms
- HTTP failures: 0.00%
- checks: 100%
- dropped iterations: 0
- max active VUs: 37

Result: PASS

43 RPS

- actual throughput: ~42.93 checkout/s
- p95: ~692.76 ms
- HTTP failures: 0.00%
- checks: 100%
- dropped iterations: 0
- max active VUs: 32

Result: PASS

44 RPS

- actual completed throughput: ~40.70 checkout/s
- p90: ~5.71 s
- p95: ~6.32 s
- max latency: ~7.58 s
- HTTP failures: ~13.38%
- checks passed: ~86.61%
- dropped iterations: 123
- max active VUs: 223

Result: FAIL

45 RPS

- actual throughput: ~43.90 checkout/s
- p95: ~1.59 s
- HTTP failures: 0.00%
- checks: 100%
- dropped iterations: 0

Result: FAIL due to latency SLO violation

50 RPS

- p90: ~8.56 s
- p95: ~9.85 s
- max latency: ~11.14 s
- HTTP failures: ~2.99%
- checks passed: ~97%
- dropped iterations: 228
- max VUs: 250/250

k6 reported insufficient VUs.

Result: FAIL

Maximum tested sustainable checkout rate

43 requests/second

Definition:

The highest tested constant checkout arrival rate that satisfied all defined SLO criteria:

- p95 < 1 second
- HTTP error rate < 1%
- dropped iterations = 0

Important:

This is the maximum tested sustainable rate for this lab environment and test duration. It is not claimed as an absolute physical limit of the application under every workload or test duration.

Observed saturation cliff

The capacity tests showed a sharp nonlinear degradation:

43 RPS:
- p95 ~693 ms
- errors 0%
- drops 0
- PASS

44 RPS:
- p95 ~6.32 s
- errors ~13.38%
- drops 123
- FAIL

50 RPS:
- p95 ~9.85 s
- errors ~2.99%
- drops 228
- max VUs 250/250
- FAIL

The platform therefore shows a clear saturation region around the low-to-mid 40 checkout requests per second under this workload.

Grafana observations

During load testing:

- FastAPI request and checkout rate increased with k6 traffic.
- Application throughput visually plateaued around the same range observed by k6.
- PostgreSQL connection count increased during tests.
- Redis command rate increased with checkout load.
- RabbitMQ ready-message backlog grew significantly and reached tens of thousands of queued messages.
- No single CPU bottleneck can be proven from the available overview dashboard because the CPU panel primarily showed current values rather than historical time-series utilization.

RabbitMQ backlog is an important performance finding, but the current evidence is not sufficient to claim that RabbitMQ alone caused the application latency saturation.

Key conclusions

1. The HA platform stayed healthy at low and moderate load.
2. Checkout latency remained below 1 second up to the tested 43 RPS level.
3. At 44 RPS the system crossed a sharp saturation boundary.
4. Above the saturation point:
   - latency increased by several seconds,
   - request errors appeared,
   - dropped iterations appeared,
   - a much larger number of concurrent VUs was required.
5. Increasing concurrency beyond the capacity point did not produce proportional throughput gains.
6. RabbitMQ message backlog increased strongly under sustained checkout load and should be investigated further if the platform is optimized.

Evidence

Recommended screenshot:

docs/screenshots/stage20-grafana-load-overview.jpg

The screenshot should show:

- host availability
- CPU/RAM overview
- PostgreSQL connections
- Redis command rate
- FastAPI request rate
- checkout rate
- RabbitMQ ready-message backlog

Result

Stage 20 established a measured performance baseline and a tested sustainable application capacity.

Maximum tested sustainable checkout rate:

43 requests/second

SLO:

p95 < 1 second
HTTP errors < 1%
dropped iterations = 0

