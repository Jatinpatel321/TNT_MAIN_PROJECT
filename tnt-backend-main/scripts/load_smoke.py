import argparse
import asyncio
import time

import httpx


async def worker(client: httpx.AsyncClient, base_url: str, requests_count: int, timeout: float) -> tuple[int, int]:
    success = 0
    failure = 0
    for _ in range(requests_count):
        try:
            response = await client.get(f"{base_url}/health/live", timeout=timeout)
            if response.status_code == 200:
                success += 1
            else:
                failure += 1
        except Exception:
            failure += 1
    return success, failure


async def run(base_url: str, concurrency: int, requests_per_worker: int, timeout: float) -> None:
    started = time.perf_counter()
    async with httpx.AsyncClient() as client:
        tasks = [
            worker(client, base_url, requests_per_worker, timeout)
            for _ in range(concurrency)
        ]
        results = await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - started
    total_success = sum(success for success, _ in results)
    total_failure = sum(failure for _, failure in results)
    total_requests = total_success + total_failure

    rps = total_requests / elapsed if elapsed > 0 else 0.0
    print(f"total_requests={total_requests}")
    print(f"success={total_success}")
    print(f"failure={total_failure}")
    print(f"elapsed_seconds={elapsed:.2f}")
    print(f"requests_per_second={rps:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TNT load smoke script")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests-per-worker", type=int, default=25)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()

    asyncio.run(
        run(
            base_url=args.base_url,
            concurrency=args.concurrency,
            requests_per_worker=args.requests_per_worker,
            timeout=args.timeout,
        )
    )
