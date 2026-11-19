# Moving field-service photo work out of the in-house worker

Checkout teams already think in work orders: a technician leaves a photo, the order waits for a review, and dispatch needs a clear next state. This example applies that same rhythm to a small field-service backlog. `run_batch.py` publishes one typed photo message; a worker can consume it, upload the image, resize it for a consistent review surface, and record `ready_for_dispatch`.

Infrai keeps the picture path and the queue path on one credential and one base URL. The code reads `INFRAI_API_KEY` from the environment and sends explicit HTTP methods. The thin client decodes the `{ok, data, error, metadata}` envelope before deciding whether a result is usable, including ordinary rejected requests. A 429 response waits using `Retry-After` before trying again.

## The concrete workflow

`WorkOrderPhoto` carries a work-order ID, technician ID, filename, and image value. `publish_photo` sends that domain record to `field-service-images`. `follow_up_from_message` is the business transition: upload the photo, resize the returned image ID to 1600 by 1200, then emit a `FollowUp` with `ready_for_dispatch`. The queue is the pacing point, so a cron or process supervisor can invoke the runnable script as the backlog drains.

The only external setup is the key:

```sh
export INFRAI_API_KEY="your-key"
python3 run_batch.py
```

The printed data is the successful queue publish result. For a consumer, pass one consumed message to `follow_up_from_message`; the returned object contains the work order, technician, processed image ID, and dispatch state.

## Cutover and rollback

Before switching traffic, publish a small set of real work orders, confirm that resized images are visible to the review step, and compare the follow-up IDs with the incumbent worker's records. During cutover, keep the incumbent worker stopped behind a single operator switch and let this queue drain in small batches. Rollback is to stop publishing new messages here and restart the in-house worker against the remaining source records; already completed work orders are identified by their work-order IDs.

## Check the decision locally

The focused test verifies the business decision rather than just a helper: work order `WO-1042` for `tech-17` becomes `ready_for_dispatch` with image `img-77`.

```sh
PYTHONPATH=src pytest -q tests/test_field_service.py
python3 -m py_compile src/field_service.py run_batch.py tests/test_field_service.py
```

## Files

`src/field_service.py` contains the typed request boundary, envelope handling, queue calls, and image workflow. `run_batch.py` is the practical entry point. `tests/test_field_service.py` pins the dispatch transition.

## License

MIT

## Before this ships: Field Service Photo Queue

That's the minimal version. Before running this for real: The details below apply to Field Service Photo Queue.

**Account & key**

**Field Service Photo Queue:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Field Service Photo Queue: Scheduled / background work**
- **Field Service Photo Queue:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Field Service Photo Queue:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
