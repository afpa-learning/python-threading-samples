import asyncio
async def long_task():
   await asyncio.sleep(5)
async def main():
   try:
       async with asyncio.timeout(3): # Limite à 3 secondes
           await long_task()
   except TimeoutError:
       print("La tâche a pris trop de temps")
asyncio.run(main())