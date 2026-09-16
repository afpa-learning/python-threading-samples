import asyncio
async def main():
   print("Début")
   await asyncio.sleep(1) # Suspend l'exécution pendant 1 seconde
   print("Fin")
asyncio.run(main()) # Exécute la coroutine