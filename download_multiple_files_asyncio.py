import asyncio
import aiohttp
from urllib.parse import urlparse
import os
from tqdm import tqdm

async def download_file(session,url):
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    async with session.get(url) as resp:
        if resp.status == 200:
            file_size = int(resp.headers['Content-Length'])
            with open(file_name, 'wb') as fd,tqdm(
                desc=file_name,
                total=file_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                progress = 0
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break
                    fd.write(chunk)
                    size=len(chunk)
                    progress += size
                    percentage = (progress / file_size) * 100
                    bar.update(size)
                    #print(f"Download Progress: {percentage:.2f}%")
        else:
            print("Failed to download the file.")

async def main():
    urls = ['https://download.oracle.com/java/21/latest/jdk-21_windows-x64_bin.zip', 'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.3.11-signed.msi', 'https://www.python.org/ftp/python/3.14.7/python-3.14.7-amd64.exe']
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(download_file(session,url)) for url in urls]
        await asyncio.gather(*tasks)

asyncio.run(main())