import asyncio
import time
def blocking_function(x, y):
   time.sleep(2)
   print(f"Résultat : {x + y}")
async def main():
   await asyncio.to_thread(blocking_function, 3, 4) # Exécute dans un thread
asyncio.run(main())