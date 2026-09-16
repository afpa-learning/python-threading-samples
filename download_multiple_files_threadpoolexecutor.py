import concurrent.futures
from tqdm import tqdm
import requests
from requests.exceptions import RequestException

def download(url, dest_path):
    try:
        response = requests.get(url, stream=True, allow_redirects=True)
        response.raise_for_status()  # Raises an exception for HTTP error status codes
        total_size = int(response.headers.get('content-length', 0))
        with open(dest_path, 'wb') as file, tqdm(
            desc=dest_path,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
                bar.update(size)
    except RequestException as e:
        print(f"Error during download: {e}")
    except IOError as e:
        print(f"Error writing file: {e}")


def download_multiple(urls, dest_paths):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download, url, path) for url, path in zip(urls, dest_paths)]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Total Progress"):
            future.result()

# Usage
urls = ['https://download.oracle.com/java/21/latest/jdk-21_windows-x64_bin.zip', 'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.3.11-signed.msi', 'https://www.python.org/ftp/python/3.14.7/python-3.14.7-amd64.exe']
paths = ['jdk-21_windows-x64_bin.zip', 'mongodb-windows-x86_64-8.3.11-signed.msi','python-3.14.7-amd64.exe']
download_multiple(urls, paths)