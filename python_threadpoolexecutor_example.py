from concurrent.futures import ThreadPoolExecutor

def worker(task):
    print(f"Task {task} running")

# Create a thread pool with 2 workers
with ThreadPoolExecutor(max_workers=2) as executor:
    # Submit two tasks to run in parallel
    executor.submit(worker, 1)
    executor.submit(worker, 2)