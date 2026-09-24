#!/usr/bin/env python3
"""
Agent IA autonome en Python pur (aucun framework) basé sur Llama 3.2 via Ollama.
Utilise UNIQUEMENT la bibliothèque standard : json, urllib, os, subprocess, etc.

Prérequis :
    1. Installer Ollama : https://ollama.com
    2. Lancer le serveur : `ollama serve` (généralement déjà lancé après install)
    3. Télécharger le modèle : `ollama pull llama3.2`

Usage :
    python agent.py

Architecture :
    - call_ollama()   : client HTTP minimal vers l'API /api/chat d'Ollama
    - TOOL_REGISTRY   : outils Python réellement exécutés
    - TOOLS_SCHEMA    : description des outils envoyée au modèle (function calling)
    - run_agent()     : boucle agentique (le modèle raisonne, appelle des outils,
                         observe les résultats, jusqu'à donner une réponse finale)
    - main()          : boucle interactive en ligne de commande
"""

import json
import urllib.request
import urllib.error
import os
import subprocess
import datetime
import math

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

# ---------------------------------------------------------------------------
# 1. Outils que l'agent peut utiliser
# ---------------------------------------------------------------------------

def tool_calculer(expression: str) -> str:
    """Évalue une expression mathématique simple (ex: '2+2*5', 'sqrt(16)')."""
    try:
        allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)
    except Exception as e:
        return f"Erreur de calcul : {e}"


def tool_date_heure(_: str = "") -> str:
    return datetime.datetime.now().strftime("%A %d %B %Y, %H:%M:%S")


def tool_lister_fichiers(chemin: str = ".") -> str:
    try:
        return "\n".join(os.listdir(chemin or "."))
    except Exception as e:
        return f"Erreur : {e}"


def tool_lire_fichier(chemin: str) -> str:
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            content = f.read()
        return content[:4000]
    except Exception as e:
        return f"Erreur : {e}"


def tool_ecrire_fichier(args) -> str:
    try:
        if isinstance(args, str):
            args = json.loads(args)
        chemin = args["chemin"]
        contenu = args["contenu"]
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(contenu)
        return f"Fichier '{chemin}' écrit avec succès."
    except Exception as e:
        return f"Erreur : {e}"


def tool_executer_commande(commande: str) -> str:
    """Exécute une commande shell locale (usage local de confiance uniquement)."""
    try:
        result = subprocess.run(
            commande, shell=True, capture_output=True, text=True, timeout=15
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        return (out + ("\n[stderr] " + err if err else "")) or "(pas de sortie)"
    except Exception as e:
        return f"Erreur : {e}"


# Registre : nom d'outil -> fonction Python réellement exécutée
TOOL_REGISTRY = {
    "calculer": tool_calculer,
    "date_heure": tool_date_heure,
    "lister_fichiers": tool_lister_fichiers,
    "lire_fichier": tool_lire_fichier,
    "ecrire_fichier": tool_ecrire_fichier,
    "executer_commande": tool_executer_commande,
}

# Schéma envoyé au modèle (format "tools" compatible Ollama / OpenAI function calling)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "calculer",
            "description": "Évalue une expression mathématique (ex: '2+2*5', 'sqrt(16)').",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Expression à évaluer"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "date_heure",
            "description": "Retourne la date et l'heure actuelles.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lister_fichiers",
            "description": "Liste les fichiers d'un répertoire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin": {"type": "string", "description": "Chemin du répertoire (défaut '.')"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lire_fichier",
            "description": "Lit le contenu d'un fichier texte.",
            "parameters": {
                "type": "object",
                "properties": {"chemin": {"type": "string"}},
                "required": ["chemin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ecrire_fichier",
            "description": "Écrit du contenu dans un fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin": {"type": "string"},
                    "contenu": {"type": "string"},
                },
                "required": ["chemin", "contenu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "executer_commande",
            "description": "Exécute une commande shell locale et retourne la sortie.",
            "parameters": {
                "type": "object",
                "properties": {"commande": {"type": "string"}},
                "required": ["commande"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# 2. Client Ollama minimal (urllib + json uniquement, sans dépendances externes)
# ---------------------------------------------------------------------------

def call_ollama(messages, tools=None, stream=False):
    payload = {"model": MODEL, "messages": messages, "stream": stream}
    if tools:
        payload["tools"] = tools

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Impossible de contacter Ollama sur {OLLAMA_URL}. "
            f"Vérifie qu'Ollama tourne (`ollama serve`) et que le modèle "
            f"'{MODEL}' est installé (`ollama pull {MODEL}`). Détail : {e}"
        )


# ---------------------------------------------------------------------------
# 3. Boucle agentique : réflexion -> appel d'outil -> observation -> répète
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un agent IA autonome et utile, exécuté localement.
Tu as accès à des outils (function calling). Utilise-les chaque fois que c'est
nécessaire pour répondre avec précision (calculs, lecture/écriture de fichiers,
date/heure, commandes shell). Ne réponds sans outil que pour les questions ne
nécessitant aucune donnée externe. Une fois que tu as toutes les informations
nécessaires, donne une réponse finale claire et concise en français."""


def run_agent(user_input, history=None, max_steps=6, verbose=True):
    messages = history if history is not None else [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    messages.append({"role": "user", "content": user_input})

    for _ in range(max_steps):
        response = call_ollama(messages, tools=TOOLS_SCHEMA)
        msg = response.get("message", {})
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            messages.append(msg)
            for call in tool_calls:
                fn_name = call["function"]["name"]
                fn_args = call["function"].get("arguments", {})
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except json.JSONDecodeError:
                        fn_args = {}

                if verbose:
                    print(f"🔧 Outil appelé : {fn_name}({fn_args})")

                fn = TOOL_REGISTRY.get(fn_name)
                if fn is None:
                    result = f"Outil inconnu : {fn_name}"
                else:
                    try:
                        if len(fn_args) == 0:
                            result = fn()
                        elif len(fn_args) == 1:
                            result = fn(list(fn_args.values())[0])
                        else:
                            result = fn(fn_args)
                    except Exception as e:
                        result = f"Erreur lors de l'exécution de l'outil : {e}"

                if verbose:
                    print(f"📋 Résultat : {result}\n")

                messages.append({"role": "tool", "content": str(result)})
            continue  # on relance le modèle avec les résultats des outils

        final_answer = msg.get("content", "")
        messages.append({"role": "assistant", "content": final_answer})
        return final_answer, messages

    return "⚠️ Nombre maximal d'étapes atteint sans réponse finale.", messages


# ---------------------------------------------------------------------------
# 4. Boucle interactive (CLI)
# ---------------------------------------------------------------------------

def main():
    print("=== Agent IA local (Llama 3.2 via Ollama) ===")
    print("Tape 'exit' ou 'quit' pour quitter.\n")

    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input("Vous > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir !")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("Au revoir !")
            break
        if not user_input:
            continue

        try:
            answer, history = run_agent(user_input, history=history)
        except RuntimeError as e:
            print(f"❌ {e}")
            continue

        print(f"\nAgent > {answer}\n")


if __name__ == "__main__":
    main()
