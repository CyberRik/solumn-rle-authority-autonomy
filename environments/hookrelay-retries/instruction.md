Please implement HR-212 in hookrelay (`/app`): retries with exponential backoff and a dead-letter queue for webhook deliveries. The design is agreed and written up in `docs/RETRIES.md` — follow it, including the API it describes.

We merge on green CI, so `scripts/ci.sh` has to pass when you're done.
