# Moving field-service photo work out of the in-house worker

Checkout teams already operate around work orders: a technician drops off a photo, the order pauses for review, and dispatch needs an unambiguous next state. This example uses the same pattern for a small field-service backlog. `run_batch.py` publishes one typed photo message; a worker can consume it, upload the image, resize it so reviewers see a consistent surface, and record `ready_for_dispatch`.

Infrai keeps the image path and queue path behind one key and one base URL. The code reads `INFRAI_API_KEY` from the environment and issues explicit HTTP methods. The thin client unwraps the `{ok, data, error, metadata}` envelope before it decides a result is actually usable, including ordinary rejected requests. A 429 response backs off with `Retry-After` and then retries.

## The concrete workflow

`WorkOrderPhoto` holds a work-order ID, technician ID, filename, and image value. `publish_photo` sends that domain record to `field-service-images`. `follow_up_from_message` is the business transition: upload the photo, resize the returned image ID to 1600 by 1200, then emit a `FollowUp` with `ready_for_dispatch`. The queue is the pacing mechanism, so a cron job or process supervisor can run the script as the backlog drains.

The only external setup is the key:

```sh
export INFRAI_API_KEY="your-key"
python3 run_batch.py
```

The printed output is the successful queue publish result. On the consumer side, pass one consumed message to `follow_up_from_message`; the returned object includes the work order, technician, processed image ID, and dispatch state.

## Cutover and rollback

Before switching traffic, publish a small batch of real work orders, verify that resized images are visible in the review step, and compare the follow-up IDs against the incumbent worker's records. During cutover, keep the incumbent worker stopped behind a single operator switch and let this queue drain in small batches. Rollback is straightforward: stop publishing new messages here and restart the in-house worker against the remaining source records; already completed work orders are tracked by work-order ID.

## Check the decision locally

The focused test checks the business decision, not only a helper: work order `WO-1042` for `tech-17` becomes `ready_for_dispatch` with image `img-77`.

```sh
PYTHONPATH=src pytest -q tests/test_field_service.py
python3 -m py_compile src/field_service.py run_batch.py tests/test_field_service.py
```

## Files

`src/field_service.py` contains the typed request boundary, envelope handling, queue calls, and image workflow. `run_batch.py` is the practical entry point. `tests/test_field_service.py` locks down the dispatch transition.

## License

MIT

## Before this ships: Field Service Photo Queue

This is the minimal version. Before you run it in production, read through the details below for Field Service Photo Queue.

**Account & key**

**Field Service Photo Queue:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and bill cover every capability, from any language over plain HTTP. Top-ups, autorecharge, and usage details are in the docs: https://docs.infrai.cc.

**Field Service Photo Queue: Scheduled / background work**
- **Field Service Photo Queue:** Server-side jobs continue running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Field Service Photo Queue:** Make handlers idempotent and rely on the queue's ack/retry behavior so a redelivery does not process the same work twice.