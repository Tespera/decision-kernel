"""decision-kernel：从 Claude Code 会话记录蒸馏个人决策内核。"""

__version__ = "0.2.0"


def main():
    from .cli import main as _main
    _main()
