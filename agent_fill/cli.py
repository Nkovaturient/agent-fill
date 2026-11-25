from agent_fill._paths import ensure_scripts_on_path

ensure_scripts_on_path()

from pipeline import main as _pipeline_main


def main() -> None:
    _pipeline_main()


if __name__ == "__main__":
    main()