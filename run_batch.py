"""Consume one queued work order for the queue worker."""

from src.field_service import InfraiClient


def main() -> None:
    client = InfraiClient()
    receipt = client.consume_photo()
    print(receipt["data"])


if __name__ == "__main__":
    main()
