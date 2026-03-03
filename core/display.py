"""
core/display.py — Affichage terminal des réponses du Plenum
============================================================
Grille des réponses agents avec rich si disponible,
fallback texte brut sinon.

Usage :
    from core.display import display_responses, display_status

    display_responses(responses, turn=salon.turn_count)
    display_status({"Claude": True, "Gemini": False, ...})
"""

from agents.base_agent import AgentResponse

try:
    from rich.console import Console
    from rich.columns import Columns
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Interface publique ───────────────────────────────────────────────────────

def display_responses(responses: dict[str, AgentResponse], turn: int = 0) -> None:
    """Affiche la grille des réponses après chaque broadcast()."""
    if HAS_RICH:
        _display_rich(responses, turn)
    else:
        _display_plain(responses, turn)


def display_status(agents_status: dict[str, bool]) -> None:
    """Affiche l'état des agents (après initialize() ou /status)."""
    if HAS_RICH:
        _status_rich(agents_status)
    else:
        _status_plain(agents_status)


def display_banner() -> None:
    """Affiche le bandeau d'accueil."""
    if HAS_RICH:
        console = Console()
        console.print(
            "\n[bold cyan]╔══════════════════════════════════════════════════════════╗[/bold cyan]"
        )
        console.print(
            "[bold cyan]║[/bold cyan]          [bold white]PLENUM  —  Salon Multi-IA[/bold white]             [bold cyan]║[/bold cyan]"
        )
        console.print(
            "[bold cyan]║[/bold cyan]   [dim]Claude · Gemini · DeepSeek · ChatGPT · Kimi[/dim]    [bold cyan]║[/bold cyan]"
        )
        console.print(
            "[bold cyan]╚══════════════════════════════════════════════════════════╝[/bold cyan]\n"
        )
    else:
        print("╔══════════════════════════════════════════════════════════╗")
        print("║          PLENUM  —  Salon Multi-IA                       ║")
        print("║   Claude · Gemini · DeepSeek · ChatGPT · Kimi            ║")
        print("╚══════════════════════════════════════════════════════════╝\n")


# ── Rich ─────────────────────────────────────────────────────────────────────

def _display_rich(responses: dict[str, AgentResponse], turn: int) -> None:
    console = Console()
    console.print(f"\n[bold cyan]═══ Tour {turn} ═══[/bold cyan]\n")

    panels = []
    for name, resp in responses.items():
        if resp.success:
            header = Text(f"✓  {resp.latency_ms:.0f}ms", style="green dim")
            panel = Panel(
                f"{header}\n\n{resp.content}",
                title=f"[bold green]{name}[/bold green]",
                border_style="green",
            )
        else:
            error = resp.error or "Erreur inconnue"
            panel = Panel(
                f"[red]✗[/red]  {error}",
                title=f"[bold red]{name}[/bold red]",
                border_style="red",
            )
        panels.append(panel)

    console.print(Columns(panels, equal=True, expand=True))
    console.print()


def _status_rich(agents_status: dict[str, bool]) -> None:
    console = Console()
    console.print("\n[bold]État des agents :[/bold]")
    for name, ok in agents_status.items():
        icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
        label = "OK" if ok else "INDISPONIBLE"
        console.print(f"  {icon}  {name} — {label}")
    console.print()


# ── Texte brut ───────────────────────────────────────────────────────────────

def _display_plain(responses: dict[str, AgentResponse], turn: int) -> None:
    print(f"\n{'═' * 72}")
    print(f"  Tour {turn}")
    print('═' * 72)

    for name, resp in responses.items():
        bar = '─' * (68 - len(name))
        print(f"\n┌── {name} {bar}")
        if resp.success:
            print(f"│  ✓  {resp.latency_ms:.0f}ms")
            print("│")
            lines = resp.content.split('\n')
            for line in lines[:25]:
                print(f"│  {line}")
            if len(lines) > 25:
                print(f"│  ...")
        else:
            print(f"│  ✗  {resp.error or 'Erreur'}")
        print(f"└{'─' * 71}")

    print()


def _status_plain(agents_status: dict[str, bool]) -> None:
    print("\nÉtat des agents :")
    for name, ok in agents_status.items():
        icon = "✓" if ok else "✗"
        label = "OK" if ok else "INDISPONIBLE"
        print(f"  {icon}  {name} — {label}")
    print()
